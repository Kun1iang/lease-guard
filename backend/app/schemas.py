"""Request and response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    review_quota: int
    question_quota: int
    reviews_used: int
    questions_used: int

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class TextDocumentRequest(BaseModel):
    title: str = Field(default="粘贴的租赁合同", max_length=120)
    text: str = Field(min_length=20)


class DocumentOut(BaseModel):
    id: str
    filename: str
    mime_type: str
    parse_status: str
    page_count: int
    ocr_used: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewCreateRequest(BaseModel):
    document_id: str
    city: str = ""


class ReviewOut(BaseModel):
    id: str
    document_id: str
    status: str
    stage: str
    progress: int
    summary: str
    error_code: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EvidenceOut(BaseModel):
    page_no: int
    quote: str
    kind: str
    verified: bool

    model_config = {"from_attributes": True}


class FindingOut(BaseModel):
    id: str
    rule_id: str
    category: str
    title: str
    severity: str
    status: str
    summary: str
    impact: str
    suggestion: str
    legal_basis: list[dict]
    user_action: str | None
    evidence: list[EvidenceOut]

    model_config = {"from_attributes": True}


class QaRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    city: str = ""


class CitationOut(BaseModel):
    source_id: str
    source_title: str
    article: str
    effective_date: str
    quote: str
    official_url: str


class QaResponse(BaseModel):
    in_scope: bool
    answer: str
    citations: list[CitationOut]
    limitations: list[str]
