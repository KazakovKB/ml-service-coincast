import os
from fastapi import APIRouter

router = APIRouter(prefix="/models", tags=["Models"])

AVAILABLE_MODELS = [
    m.strip() for m in os.getenv("AVAILABLE_MODELS", "Demo").split(",") if m.strip()
]

@router.get("/", response_model=list[str])
def list_models() -> list[str]:
    return AVAILABLE_MODELS