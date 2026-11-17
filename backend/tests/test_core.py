from __future__ import annotations

from app.clauses import segment_clauses
from app.graph import build_review_graph
from app.knowledge import is_rental_scope
from app.llm import redact_pii
from app.parsers import parse_text
from app.services import SAMPLE_PATH


def test_sample_contract_rules_have_verified_evidence():
    parsed = parse_text(SAMPLE_PATH.read_text(encoding="utf-8"))
    pages = [{"page_no": page.page_no, "text": page.text} for page in parsed.pages]
    clauses = segment_clauses(pages)
    result = build_review_graph().invoke({"pages": pages})
    findings = result["findings"]

    assert len(clauses) >= 10
    assert len(findings) >= 6
    assert any(item["rule_id"] == "REPAIR_SHIFTED" for item in findings)
    assert all(item["verified"] for item in findings if item["evidence_kind"] == "exact")


def test_rental_scope_guard_rejects_other_topics():
    assert is_rental_scope("押金退还是否要写具体天数")
    assert is_rental_scope("房东可以随时进入房屋吗")
    assert not is_rental_scope("劳动合同被辞退怎么赔偿")
    assert not is_rental_scope("你好，帮我写一份论文")


def test_redact_pii():
    text = "姓名：张三 手机号 13812345678 身份证 510101199001011234"
    redacted = redact_pii(text)
    assert "13812345678" not in redacted
    assert "510101199001011234" not in redacted
    assert "[手机号]" in redacted
