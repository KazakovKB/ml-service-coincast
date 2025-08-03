from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from src.app.api.schemas import UserCreate, Token
from src.app.api.deps import get_auth_service
from src.app.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=Token, status_code=201)
def register(payload: UserCreate, svc: AuthService = Depends(get_auth_service)):
    try:
        return svc.register(payload.email, payload.password)
    except AuthService.EmailExists:
        raise HTTPException(400, "Email already registered")


@router.post("/login", response_model=Token)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    svc: AuthService = Depends(get_auth_service),
):
    try:
        return svc.login(form.username, form.password)
    except AuthService.BadCredentials:
        raise HTTPException(401, "Bad credentials")