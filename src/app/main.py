from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.api import router as api_router
from src.app.infra.mq import start_broker, stop_broker

app = FastAPI(
    title="ML-Service-Coincast",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#  Подключаем все роутеры
app.include_router(api_router)

@app.on_event("startup")
async def _mq_start():
    await start_broker()

@app.on_event("shutdown")
async def _mq_stop():
    await stop_broker()