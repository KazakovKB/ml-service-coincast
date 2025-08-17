import os
from fastapi import APIRouter
from src.app.infra.ml.registry import list_names

router = APIRouter(prefix="/models", tags=["Models"])

_ALLOWED = [s.strip() for s in os.getenv("AVAILABLE_MODELS", "").split(",") if s.strip()] or None

@router.get("/", response_model=list[str])
def list_models() -> list[str]:
    return list_names(_ALLOWED)