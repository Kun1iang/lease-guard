"""Optional OpenAI-compatible model integration with strict fallbacks."""

from __future__ import annotations

import re

import httpx
import structlog

from app.config import get_settings
from app.knowledge import KnowledgeEntry

logger = structlog.get_logger(__name__)


def redact_pii(text: str) -> str:
    text = re.sub(r"\b\d{17}[\dXx]\b", "[身份证]", text)
    text = re.sub(r"(?<!\d)1[3-9]\d{9}(?!\d)", "[手机号]", text)
    text = re.sub(r"(?:[\u4e00-\u9fff]{2,}(?:省|市|区))[\u4e00-\u9fff\dA-Za-z\-]{3,}", "[详细地址]", text)
    text = re.sub(r"\b\d{12,19}\b", "[账号]", text)
    text = re.sub(r"(姓名[:：]\s*)[\u4e00-\u9fff]{2,4}", r"\1[姓名]", text)
    return text


class LLMService:
    @property
    def available(self) -> bool:
        settings = get_settings()
        return settings.enable_llm and bool(settings.llm_base_url and settings.llm_api_key)

    async def answer_rental_question(
        self,
        question: str,
        entries: list[KnowledgeEntry],
        fallback: str,
    ) -> str:
        if not self.available or not entries:
            return fallback
        settings = get_settings()
        source_text = "\n\n".join(
            f"[{entry.id}] {entry.source_title} {entry.article}\n{entry.content}" for entry in entries
        )
        prompt = (
            "你是中国大陆住宅租赁合同解释助手。只回答租房问题。"
            "只能依据给出的资料，不得补充资料外事实。回答末尾提示不构成正式法律意见。\n\n"
            f"资料：\n{source_text}\n\n问题：{redact_pii(question)}"
        )
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                    json={
                        "model": settings.llm_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                    },
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:  # noqa: BLE001 - model failure must fall back
            logger.warning("llm.failed", error=type(exc).__name__)
            return fallback

    async def summarize_review(self, finding_count: int, severities: dict[str, int]) -> str:
        fallback = (
            f"本次共识别 {finding_count} 项风险，其中高风险 {severities.get('high', 0)} 项、"
            f"中风险 {severities.get('medium', 0)} 项、低风险 {severities.get('low', 0)} 项。"
            "请优先核对押金、维修、提前解约和缺失条款。"
        )
        if not self.available:
            return fallback
        settings = get_settings()
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                    json={
                        "model": settings.llm_model,
                        "messages": [
                            {
                                "role": "user",
                                "content": (f"用两句话总结住宅租赁合同审阅结果，不要给法律结论：{fallback}"),
                            }
                        ],
                        "temperature": 0.1,
                    },
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:  # noqa: BLE001
            logger.warning("llm.summary_failed", error=type(exc).__name__)
            return fallback
