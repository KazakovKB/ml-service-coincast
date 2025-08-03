from datetime import datetime, timedelta, UTC
from typing import Generator

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from src.app.infra.db import SessionLocal
from src.app.infra.repositories import UserRepo, AccountRepo
from src.app.services.auth_service import AuthService
from src.app.services.account_service import AccountService

import os

SECRET = os.getenv('SECRET')
ALGO   = os.getenv('ALGO')
oauth2  = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# JWT хелперы
def create_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(UTC) + timedelta(hours=12)
    }
    return jwt.encode(payload, SECRET, ALGO)


def get_current_user(
    token: str = Depends(oauth2),
    db: Session = Depends(get_db)
):
    try:
        user_id = int(jwt.decode(token, SECRET, algorithms=[ALGO])["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(401, "Invalid token")
    repo = UserRepo(db)
    try:
        return repo.get(user_id)
    except ValueError:
        raise HTTPException(404, "User not found")


# сервис-фабрики
def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(UserRepo(db), AccountRepo(db), create_token)

def get_account_service(db: Session = Depends(get_db)) -> AccountService:
    return AccountService(AccountRepo(db))