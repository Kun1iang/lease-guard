"""Contract clause segmentation."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ClauseRecord:
    page_no: int
    heading: str
    text: str
    clause_type: str


CLAUSE_TYPES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("deposit", ("押金", "保证金")),
    ("rent", ("租金", "支付", "逾期")),
    ("fees", ("水费", "电费", "燃气", "物业", "网络")),
    ("maintenance", ("维修", "损坏", "自然损耗")),
    ("termination", ("提前退租", "解除", "违约金", "收回")),
    ("handover", ("交接", "清单", "家电", "家具")),
    ("sublease", ("转租", "转借")),
    ("renewal", ("续租", "续期")),
    ("privacy", ("进入", "检查", "隐私")),
    ("dispute", ("争议", "诉讼", "仲裁", "法院")),
)


def classify_clause(text: str) -> str:
    for name, words in CLAUSE_TYPES:
        if any(word in text for word in words):
            return name
    return "other"


def segment_clauses(pages: list[dict]) -> list[ClauseRecord]:
    combined: list[tuple[int, str]] = []
    for page in pages:
        combined.append((int(page["page_no"]), str(page["text"])))

    records: list[ClauseRecord] = []
    pattern = re.compile(
        r"(?m)^(第[一二三四五六七八九十百\d]+条[^\n]*|"
        r"[一二三四五六七八九十]+、[^\n]*|\d+[.、][^\n]*)"
    )
    for page_no, text in combined:
        matches = list(pattern.finditer(text))
        if not matches:
            for chunk in [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]:
                records.append(ClauseRecord(page_no, "", chunk, classify_clause(chunk)))
            continue
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            block = text[match.start() : end].strip()
            heading = match.group(1).strip()
            body = block[len(heading) :].strip()
            records.append(
                ClauseRecord(
                    page_no=page_no,
                    heading=heading[:200],
                    text=block,
                    clause_type=classify_clause(f"{heading}\n{body}"),
                )
            )
    return records or [ClauseRecord(1, "", "\n".join(t for _, t in combined), "other")]
