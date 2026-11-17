"""Database entities for accounts, documents, reviews and evidence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="user")
    review_quota: Mapped[int] = mapped_column(Integer, default=10)
    question_quota: Mapped[int] = mapped_column(Integer, default=100)
    reviews_used: Mapped[int] = mapped_column(Integer, default=0)
    questions_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(120))
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    parse_status: Mapped[str] = mapped_column(String(30), default="pending")
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    ocr_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    pages: Mapped[list[DocumentPage]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
    clauses: Mapped[list[Clause]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentPage(Base):
    __tablename__ = "document_pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    page_no: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    document: Mapped[Document] = relationship(back_populates="pages")


class Clause(Base):
    __tablename__ = "clauses"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    page_no: Mapped[int] = mapped_column(Integer)
    clause_type: Mapped[str] = mapped_column(String(40), default="other")
    heading: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text)

    document: Mapped[Document] = relationship(back_populates="clauses")


class ReviewJob(Base):
    __tablename__ = "review_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    stage: Mapped[str] = mapped_column(String(40), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str] = mapped_column(Text, default="")
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    findings: Mapped[list[RiskFinding]] = relationship(
        back_populates="review",
        cascade="all, delete-orphan",
    )


class RiskFinding(Base):
    __tablename__ = "risk_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    review_id: Mapped[str] = mapped_column(ForeignKey("review_jobs.id"), index=True)
    rule_id: Mapped[str] = mapped_column(String(80))
    category: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(160))
    severity: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30), default="confirmed")
    summary: Mapped[str] = mapped_column(Text)
    impact: Mapped[str] = mapped_column(Text)
    suggestion: Mapped[str] = mapped_column(Text)
    legal_basis: Mapped[str] = mapped_column(Text, default="[]")
    user_action: Mapped[str | None] = mapped_column(String(30), nullable=True)

    review: Mapped[ReviewJob] = relationship(back_populates="findings")
    evidence: Mapped[list[FindingEvidence]] = relationship(
        back_populates="finding",
        cascade="all, delete-orphan",
    )


class FindingEvidence(Base):
    __tablename__ = "finding_evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[str] = mapped_column(ForeignKey("risk_findings.id"), index=True)
    page_no: Mapped[int] = mapped_column(Integer)
    quote: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(30), default="exact")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)

    finding: Mapped[RiskFinding] = relationship(back_populates="evidence")


class QAAudit(Base):
    __tablename__ = "qa_audits"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    in_scope: Mapped[bool] = mapped_column(Boolean)
    citation_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
