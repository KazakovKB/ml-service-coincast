from fastapi import APIRouter
from src.app.api.auth import router as r_auth
from src.app.api.account import router as r_account
from src.app.api.prediction import router as r_pred
from src.app.api.models import router as r_models

router = APIRouter()
router.include_router(r_auth)
router.include_router(r_account)
router.include_router(r_pred)
router.include_router(r_models)