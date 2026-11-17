"""Seed the trial account."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import User
from app.security import hash_password


def seed_trial_user(db: Session) -> None:
    settings = get_settings()
    existing = db.scalar(select(User).where(User.username == settings.trial_username))
    if existing:
        return
    db.add(
        User(
            username=settings.trial_username,
            password_hash=hash_password(settings.trial_password),
            role="trial",
            review_quota=settings.trial_review_quota,
            question_quota=settings.trial_question_quota,
        )
    )
    db.commit()
