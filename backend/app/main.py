"""FastAPI application for Lease Guard."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal, create_tables, get_db
from app.dependencies import get_current_user
from app.models import Document, DocumentPage, ReviewJob, RiskFinding, User
from app.schemas import (
    DocumentOut,
    FindingOut,
    LoginRequest,
    QaRequest,
    QaResponse,
    RegisterRequest,
    ReviewCreateRequest,
    ReviewOut,
    TextDocumentRequest,
    TokenResponse,
    UserOut,
)
from app.security import create_access_token, hash_password, verify_password
from app.seed import seed_trial_user
from app.services import (
    answer_rental_question,
    create_review,
    create_sample_review,
    create_text_document,
    create_uploaded_document,
    delete_document,
    process_review,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    create_tables()
    with SessionLocal() as db:
        seed_trial_user(db)
    yield


app = FastAPI(title="Lease Guard API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        user=UserOut.model_validate(user),
    )


def _findings(db: Session, review_id: str) -> list[FindingOut]:
    rows = db.scalars(
        select(RiskFinding)
        .where(RiskFinding.review_id == review_id)
        .order_by(RiskFinding.severity.desc(), RiskFinding.title)
    ).all()
    output: list[FindingOut] = []
    for row in rows:
        output.append(
            FindingOut(
                id=row.id,
                rule_id=row.rule_id,
                category=row.category,
                title=row.title,
                severity=row.severity,
                status=row.status,
                summary=row.summary,
                impact=row.impact,
                suggestion=row.suggestion,
                legal_basis=json.loads(row.legal_basis or "[]"),
                user_action=row.user_action,
                evidence=[
                    {
                        "page_no": item.page_no,
                        "quote": item.quote,
                        "kind": item.kind,
                        "verified": item.verified,
                    }
                    for item in row.evidence
                ],
            )
        )
    return output


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "lease-guard"}


@app.post("/api/auth/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.username == payload.username)):
        raise HTTPException(status_code=409, detail="用户名已存在")
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role="user",
        review_quota=10,
        question_quota=100,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token_response(user)


@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return _token_response(user)


@app.post("/api/auth/trial", response_model=TokenResponse)
def trial_login(db: Session = Depends(get_db)):
    settings = get_settings()
    user = db.scalar(select(User).where(User.username == settings.trial_username))
    if user is None:
        seed_trial_user(db)
        user = db.scalar(select(User).where(User.username == settings.trial_username))
    return _token_response(user)


@app.get("/api/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@app.post("/api/documents/upload", response_model=DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings = get_settings()
    data = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="文件超过大小限制")
    try:
        document = create_uploaded_document(
            db,
            user.id,
            file.filename or "contract.pdf",
            file.content_type or "application/octet-stream",
            data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return document


@app.post("/api/documents/text", response_model=DocumentOut)
def submit_text(
    payload: TextDocumentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    document = create_text_document(db, user.id, payload.title, payload.text)
    return document


@app.get("/api/documents/{document_id}/pages")
def document_pages(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    document = db.get(Document, document_id)
    if document is None or document.user_id != user.id:
        raise HTTPException(status_code=404, detail="文档不存在")
    pages = db.scalars(
        select(DocumentPage).where(DocumentPage.document_id == document_id).order_by(DocumentPage.page_no)
    ).all()
    return {
        "document": DocumentOut.model_validate(document),
        "pages": [
            {"page_no": page.page_no, "text": page.text, "ocr_confidence": page.ocr_confidence}
            for page in pages
        ],
    }


@app.post("/api/reviews", response_model=ReviewOut)
def start_review(
    payload: ReviewCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    document = db.get(Document, payload.document_id)
    if document is None or document.user_id != user.id:
        raise HTTPException(status_code=404, detail="文档不存在")
    try:
        job = create_review(db, user, document)
    except ValueError as exc:
        if str(exc) == "OUT_OF_SCOPE":
            raise HTTPException(
                status_code=422,
                detail="只接受中国大陆住宅租赁合同",
            ) from exc
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    background_tasks.add_task(process_review, job.id)
    return job


@app.post("/api/reviews/sample", response_model=ReviewOut)
def sample_review(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = create_sample_review(db, user)
    background_tasks.add_task(process_review, job.id)
    return job


@app.get("/api/reviews/{review_id}", response_model=ReviewOut)
def get_review(
    review_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = db.get(ReviewJob, review_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="审阅任务不存在")
    return job


@app.get("/api/reviews", response_model=list[ReviewOut])
def list_reviews(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.scalars(
        select(ReviewJob)
        .where(ReviewJob.user_id == user.id)
        .order_by(ReviewJob.created_at.desc())
    ).all()


@app.get("/api/reviews/{review_id}/findings", response_model=list[FindingOut])
def get_findings(
    review_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = db.get(ReviewJob, review_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="审阅任务不存在")
    return _findings(db, review_id)


@app.get("/api/reviews/{review_id}/report")
def get_report(
    review_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = db.get(ReviewJob, review_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="审阅任务不存在")
    document = db.get(Document, job.document_id)
    pages = db.scalars(
        select(DocumentPage).where(DocumentPage.document_id == job.document_id).order_by(DocumentPage.page_no)
    ).all()
    return {
        "review": ReviewOut.model_validate(job),
        "document": DocumentOut.model_validate(document),
        "pages": [{"page_no": page.page_no, "text": page.text} for page in pages],
        "findings": _findings(db, review_id),
        "notice": "本报告用于合同风险预筛，不构成正式法律意见。",
    }


@app.patch("/api/findings/{finding_id}/action")
def update_finding_action(
    finding_id: str,
    action: str = Query(pattern="confirm|ignore|false_positive"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    finding = db.get(RiskFinding, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="风险不存在")
    job = db.get(ReviewJob, finding.review_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="风险不存在")
    finding.user_action = action
    db.commit()
    return {"ok": True}


@app.post("/api/rental-qa", response_model=QaResponse)
async def rental_qa(
    payload: QaRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        result = await answer_rental_question(db, user, payload.question)
    except ValueError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    return result


@app.delete("/api/documents/{document_id}")
def remove_document(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not delete_document(db, user, document_id):
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"deleted": True}


dist_dir = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if dist_dir.exists():
    if (dist_dir / "assets").exists():
        app.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def serve_spa(path: str):
        candidate = dist_dir / path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(dist_dir / "index.html")
