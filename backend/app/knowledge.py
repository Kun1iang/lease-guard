"""Rental-only legal knowledge retrieval and answer composition."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

KB_PATH = Path(__file__).parent / "data" / "legal_kb.json"
RENTAL_TERMS = {
    "租房",
    "租赁",
    "出租",
    "承租",
    "房东",
    "租客",
    "押金",
    "租金",
    "退租",
    "转租",
    "续租",
    "维修",
    "房屋",
    "水电",
    "物业",
    "交房",
    "入住",
    "退房",
    "中介",
    "合同",
    "违约",
}
OTHER_LEGAL_TERMS = {
    "劳动",
    "离婚",
    "婚姻",
    "继承",
    "刑事",
    "借款",
    "股权",
    "交通事故",
    "知识产权",
    "行政诉讼",
    "公司设立",
}


@dataclass(frozen=True)
class KnowledgeEntry:
    id: str
    title: str
    category: str
    keywords: tuple[str, ...]
    content: str
    source_title: str
    article: str
    effective_date: str
    official_url: str
    is_official: bool = True

    def citation(self) -> dict[str, str]:
        return {
            "source_id": self.id,
            "source_title": self.source_title,
            "article": self.article,
            "effective_date": self.effective_date,
            "quote": self.content,
            "official_url": self.official_url,
        }


def _load_entries() -> list[KnowledgeEntry]:
    payload = json.loads(KB_PATH.read_text(encoding="utf-8"))
    return [
        KnowledgeEntry(
            id=item["id"],
            title=item["title"],
            category=item["category"],
            keywords=tuple(item["keywords"]),
            content=item["content"],
            source_title=item["source_title"],
            article=item["article"],
            effective_date=item["effective_date"],
            official_url=item.get("official_url", ""),
            is_official=bool(item.get("is_official", True)),
        )
        for item in payload
    ]


ENTRIES = _load_entries()


def is_rental_scope(question: str) -> bool:
    text = question.strip()
    if not text:
        return False
    if any(term in text for term in OTHER_LEGAL_TERMS):
        return False
    return any(term in text for term in RENTAL_TERMS)


def is_rental_contract(text: str) -> bool:
    signals = sum(1 for term in ("房屋", "出租", "承租", "租金", "租赁", "房东") if term in text)
    return signals >= 2


def _bigrams(text: str) -> set[str]:
    compact = re.sub(r"\s|[^\u4e00-\u9fffA-Za-z0-9]", "", text)
    return {compact[i : i + 2] for i in range(max(0, len(compact) - 1))}


def retrieve(question: str, limit: int = 3) -> list[KnowledgeEntry]:
    qgrams = _bigrams(question)
    scored: list[tuple[float, KnowledgeEntry]] = []
    for entry in ENTRIES:
        keyword_score = sum(2.0 for keyword in entry.keywords if keyword in question)
        title_score = sum(1.5 for keyword in entry.keywords if keyword in entry.title)
        content_score = len(qgrams & _bigrams(entry.content)) * 0.12
        score = keyword_score + title_score + content_score
        if score > 0:
            scored.append((score, entry))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [entry for _, entry in scored[:limit]]


def citation_for_id(source_id: str) -> dict[str, Any] | None:
    for entry in ENTRIES:
        if entry.id == source_id:
            return entry.citation()
    return None


def deterministic_answer(question: str, entries: list[KnowledgeEntry]) -> str:
    if not entries:
        return "当前租房知识库没有足够依据确认这个问题。请查看官方合同文本，或咨询专业人士。"
    lines = ["按当前租房知识库，可以确认这些依据："]
    for index, entry in enumerate(entries, start=1):
        lines.append(f"{index}. {entry.content}")
    lines.append("这些内容用于解释合同风险，不构成正式法律意见。")
    return "\n".join(lines)
