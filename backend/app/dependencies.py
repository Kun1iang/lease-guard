"""FastAPI dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="请先登录")
    try:
        user_id = decode_access_token(credentials.credentials)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="登录已失效") from exc
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user
