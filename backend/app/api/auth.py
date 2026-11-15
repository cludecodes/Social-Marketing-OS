"""Auth: login, JWT, current user dependency."""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt as _jwt
from pydantic import BaseModel

from ..config import settings
from ..db import db_session
from ..models import AuditLog, User
from ..security import hash_password, verify_password

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


class LoginReq(BaseModel):
    username: str
    password: str


def create_token(user_id: int, username: str) -> str:
    exp = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _jwt.encode({"sub": username, "uid": user_id, "exp": exp}, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = _jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    with db_session() as db:
        user = db.query(User).filter_by(username=payload.get("sub")).first()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user


@router.post("/login")
def login(req: LoginReq):
    with db_session() as db:
        user = db.query(User).filter_by(username=req.username).first()
        if user is None or not verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        user.last_login = datetime.utcnow()
        token = create_token(user.id, user.username)
        db.add(AuditLog(actor=user.username, action="login", entity="auth"))
        return {"token": token, "user": {"id": user.id, "username": user.username, "role": user.role}}


@router.post("/change-password")
def change_password(req: dict, user: User = Depends(get_current_user)):
    old, new = req.get("old"), req.get("new")
    if not old or not new or len(new or "") < 8:
        raise HTTPException(status_code=400, detail="new password must be >= 8 chars")
    with db_session() as db:
        u = db.query(User).filter_by(id=user.id).first()
        if not verify_password(old or "", u.password_hash):
            raise HTTPException(status_code=401, detail="old password incorrect")
        u.password_hash = hash_password(new)
        db.add(AuditLog(actor=u.username, action="password_change", entity="auth"))
        return {"ok": True}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "role": user.role}


def seed_admin() -> None:
    with db_session() as db:
        if db.query(User).filter_by(username=settings.ADMIN_USERNAME).first() is None:
            db.add(User(username=settings.ADMIN_USERNAME, password_hash=hash_password(settings.ADMIN_PASSWORD), role="admin"))
