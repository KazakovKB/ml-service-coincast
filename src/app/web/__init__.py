from fastapi import APIRouter
from src.app.web.router import router as r_web

router = APIRouter()
router.include_router(r_web)