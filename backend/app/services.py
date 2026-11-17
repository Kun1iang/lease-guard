"""Document, review and question-answer orchestration."""

from __future__ import annotations

import asyncio
import json
import shutil
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import structlog
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.clauses import segment_clauses
from app.config import get_settings
from app.database import SessionLocal
from app.graph import build_review_graph
from app.knowledge import deterministic_answer, is_rental_contract, is_rental_scope, retrieve
from app.llm import LLMService
from app.models import Clause, Document, DocumentPage, FindingEvidence, QAAudit, ReviewJob, RiskFinding, User
from app.parsers import ParsedDocument, parse_text, parse_upload

logger = structlog.get_logger(__name__)
SAMPLE_PATH = Path(__file__).parent / "data" / "sample_contract.txt"


def _new_id() -> str:
    return str(uuid4())


def _save_parsed_document(
    db: Session,
    *,
    user_id: int,
    filename: str,
    mime_type: str,
    parsed: ParsedDocument,
    storage_path: str | None,
) -> Document:
    if not parsed.pages or not any(page.text.strip() for page in parsed.pages):
        raise ValueError("EMPTY_DOCUMENT")
    document = Document(
        id=_new_id(),
        user_id=user_id,
        filename=filename,
        mime_type=mime_type,
        storage_path=storage_path,
        parse_status="parsed",
        page_count=len(parsed.pages),
        ocr_used=parsed.ocr_used,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db.add(document)
    for page in parsed.pages:
        db.add(
            DocumentPage(
                document_id=document.id,
                page_no=page.page_no,
                text=page.text,
                ocr_confidence=page.ocr_confidence,
            )
        )
    db.commit()
    db.refresh(document)
    return document


def create_text_document(db: Session, user_id: int, title: str, text: str) -> Document:
    parsed = parse_text(text)
    return _save_parsed_document(
        db,
        user_id=user_id,
        filename=f"{title.strip() or '租赁合同'}.txt",
        mime_type="text/plain",
        parsed=parsed,
        storage_path=None,
    )


def create_uploaded_document(
    db: Session,
    user_id: int,
    filename: str,
    mime_type: str,
    data: bytes,
) -> Document:
    parsed = parse_upload(filename, mime_type, data)
    settings = get_settings()
    if len(parsed.pages) > settings.max_pages:
        raise ValueError("TOO_MANY_PAGES")
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    suffix = Path(filename).suffix.lower() or ".bin"
    stored = settings.storage_path / f"{_new_id()}{suffix}"
    stored.write_bytes(data)
    return _save_parsed_document(
        db,
        user_id=user_id,
        filename=filename,
        mime_type=mime_type,
        parsed=parsed,
        storage_path=str(stored),
    )


def create_review(
    db: Session,
    user: User,
    document: Document,
    *,
    consume_quota: bool = True,
) -> ReviewJob:
    if document.user_id != user.id:
        raise PermissionError("DOCUMENT_NOT_OWNED")
    pages = db.scalars(
        select(DocumentPage).where(DocumentPage.document_id == document.id)
    ).all()
    if not is_rental_contract("\n".join(page.text for page in pages)):
        raise ValueError("OUT_OF_SCOPE")
    if consume_quota and user.reviews_used >= user.review_quota:
        raise ValueError("REVIEW_QUOTA_EXCEEDED")
    job = ReviewJob(
        id=_new_id(),
        document_id=document.id,
        user_id=user.id,
        status="queued",
        stage="queued",
        progress=5,
    )
    db.add(job)
    if consume_quota:
        user.reviews_used += 1
    db.commit()
    db.refresh(job)
    return job


def create_sample_review(db: Session, user: User) -> ReviewJob:
    text = SAMPLE_PATH.read_text(encoding="utf-8")
    document = create_text_document(db, user.id, "脱敏住宅租赁合同样例", text)
    return create_review(db, user, document, consume_quota=False)


def _clear_review_findings(db: Session, review_id: str) -> None:
    finding_ids = db.scalars(select(RiskFinding.id).where(RiskFinding.review_id == review_id)).all()
    if finding_ids:
        db.execute(delete(FindingEvidence).where(FindingEvidence.finding_id.in_(finding_ids)))
        db.execute(delete(RiskFinding).where(RiskFinding.id.in_(finding_ids)))


def process_review(review_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(ReviewJob, review_id)
        if job is None:
            return
        job.status = "running"
        job.stage = "segmentation"
        job.progress = 20
        db.commit()

        pages = db.scalars(
            select(DocumentPage)
            .where(DocumentPage.document_id == job.document_id)
            .order_by(DocumentPage.page_no)
        ).all()
        page_data = [{"page_no": page.page_no, "text": page.text} for page in pages]

        db.execute(delete(Clause).where(Clause.document_id == job.document_id))
        clauses = segment_clauses(page_data)
        for clause in clauses:
            db.add(
                Clause(
                    document_id=job.document_id,
                    page_no=clause.page_no,
                    clause_type=clause.clause_type,
                    heading=clause.heading,
                    text=clause.text,
                )
            )
        db.commit()

        job.stage = "rule_check"
        job.progress = 45
        db.commit()
        result = build_review_graph().invoke({"pages": page_data})
        findings = result.get("findings", [])

        job.stage = "evidence_verification"
        job.progress = 75
        db.commit()
        _clear_review_findings(db, job.id)
        for finding in findings:
            finding_id = _new_id()
            db.add(
                RiskFinding(
                    id=finding_id,
                    review_id=job.id,
                    rule_id=finding["rule_id"],
                    category=finding["category"],
                    title=finding["title"],
                    severity=finding["severity"],
                    status=finding.get("status", "needs_review"),
                    summary=finding["summary"],
                    impact=finding["impact"],
                    suggestion=finding["suggestion"],
                    legal_basis=json.dumps(
                        finding.get("legal_basis", []),
                        ensure_ascii=False,
                    ),
                )
            )
            db.add(
                FindingEvidence(
                    finding_id=finding_id,
                    page_no=int(finding.get("page_no", 1)),
                    quote=str(finding.get("quote", "")),
                    kind=str(finding.get("evidence_kind", "exact")),
                    verified=bool(finding.get("verified", False)),
                )
            )
        db.commit()

        severities = Counter(item["severity"] for item in findings)
        job.summary = asyncio.run(LLMService().summarize_review(len(findings), dict(severities)))
        job.status = "succeeded"
        job.stage = "completed"
        job.progress = 100
        job.completed_at = datetime.now(UTC)
        db.commit()
    except Exception as exc:  # noqa: BLE001 - worker must persist failure state
        logger.exception("review.failed", review_id=review_id)
        job = db.get(ReviewJob, review_id)
        if job:
            job.status = "failed"
            job.stage = "failed"
            job.error_code = type(exc).__name__
            db.commit()
    finally:
        db.close()


async def answer_rental_question(db: Session, user: User, question: str) -> dict:
    if not is_rental_scope(question):
        db.add(QAAudit(user_id=user.id, in_scope=False, citation_count=0))
        db.commit()
        return {
            "in_scope": False,
            "answer": "本服务只回答中国大陆住宅租赁相关问题，例如押金、维修、退租、续租和房屋交接。",
            "citations": [],
            "limitations": ["不提供租房之外的法律或生活咨询"],
        }
    if user.questions_used >= user.question_quota:
        raise ValueError("QUESTION_QUOTA_EXCEEDED")

    entries = retrieve(question)
    fallback = deterministic_answer(question, entries)
    answer = await LLMService().answer_rental_question(question, entries, fallback)
    user.questions_used += 1
    db.add(QAAudit(user_id=user.id, in_scope=True, citation_count=len(entries)))
    db.commit()
    return {
        "in_scope": True,
        "answer": answer,
        "citations": [entry.citation() for entry in entries],
        "limitations": ["风险提示不构成正式法律意见"],
    }


def delete_document(db: Session, user: User, document_id: str) -> bool:
    document = db.get(Document, document_id)
    if document is None or document.user_id != user.id:
        return False
    reviews = db.scalars(select(ReviewJob).where(ReviewJob.document_id == document_id)).all()
    for review in reviews:
        _clear_review_findings(db, review.id)
        db.delete(review)
    db.execute(delete(Clause).where(Clause.document_id == document_id))
    db.execute(delete(DocumentPage).where(DocumentPage.document_id == document_id))
    stored = Path(document.storage_path) if document.storage_path else None
    db.delete(document)
    db.commit()
    if stored and stored.exists():
        try:
            stored.unlink()
        except OSError:
            shutil.rmtree(stored, ignore_errors=True)
    return True
