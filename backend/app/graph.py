"""LangGraph review pipeline: rules, legal basis and evidence verification."""

from __future__ import annotations

import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.knowledge import citation_for_id
from app.rules import evaluate_rules


class ReviewState(TypedDict, total=False):
    pages: list[dict[str, Any]]
    matches: list[dict[str, Any]]
    findings: list[dict[str, Any]]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text)


def run_rules(state: ReviewState) -> dict:
    matches = evaluate_rules(state.get("pages", []))
    return {"matches": [match.__dict__ for match in matches]}


def attach_legal_basis(state: ReviewState) -> dict:
    findings: list[dict[str, Any]] = []
    for match in state.get("matches", []):
        citations = [
            citation
            for source_id in match.get("legal_basis_ids", ())
            if (citation := citation_for_id(source_id))
        ]
        findings.append({**match, "legal_basis": citations})
    return {"findings": findings}


def verify_evidence(state: ReviewState) -> dict:
    page_map = {int(page["page_no"]): _normalize(str(page["text"])) for page in state.get("pages", [])}
    findings = []
    for finding in state.get("findings", []):
        item = dict(finding)
        quote = str(item.get("quote") or "")
        page_no = int(item.get("page_no") or 1)
        if item.get("evidence_kind") == "absence":
            item["verified"] = True
            item["status"] = "needs_review"
        elif quote and _normalize(quote) in page_map.get(page_no, ""):
            item["verified"] = True
            item["status"] = "confirmed"
        else:
            item["verified"] = False
            item["status"] = "needs_review"
        findings.append(item)
    return {"findings": findings}


def build_review_graph():
    builder = StateGraph(ReviewState)
    builder.add_node("run_rules", run_rules)
    builder.add_node("attach_legal_basis", attach_legal_basis)
    builder.add_node("verify_evidence", verify_evidence)
    builder.add_edge(START, "run_rules")
    builder.add_edge("run_rules", "attach_legal_basis")
    builder.add_edge("attach_legal_basis", "verify_evidence")
    builder.add_edge("verify_evidence", END)
    return builder.compile()
