from fastapi import APIRouter, Depends, HTTPException, status
from src.app.api.schemas import PredictionIn, PredictionOut, PredictionShort
from src.app.api.deps import get_current_user, get_db
from src.app.infra.mq import enqueue_predict
from src.app.infra.repositories import AccountRepo, PredictionRepo
from src.app.services.prediction_service import PredictionService
import os


router = APIRouter(prefix="/predict", tags=["Prediction"])
COST_PER_ROW = int(os.getenv("COST_PER_ROW"))


@router.post("/", response_model=PredictionShort, status_code=status.HTTP_202_ACCEPTED)
async def predict(
    payload: PredictionIn,
    user = Depends(get_current_user),
    db   = Depends(get_db),
):
    # Предварительная оценка и проверка средств
    est_cost = len(payload.data) * COST_PER_ROW
    balance = AccountRepo(db).load(user.account.id).balance
    if balance < est_cost:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "Not enough credits")

    # Создаём pending-запись
    pred_repo = PredictionRepo(db)
    pending = pred_repo.create_pending(owner_id=user.id, model_name=payload.model_name)

    # Отправляем задачу в очередь
    await enqueue_predict({
        "job_id":     pending.id,
        "user_id":    user.id,
        "account_id": user.account.id,
        "model":      payload.model_name,
        "data":       payload.data,
    })

    return pending


@router.get("/history", response_model=list[PredictionShort])
def history(
    user = Depends(get_current_user),
    db   = Depends(get_db),
):
    svc = PredictionService(AccountRepo(db), PredictionRepo(db))
    return svc.history(user.id)


@router.get("/{job_id:int}", response_model=PredictionOut)
def get_job(
    job_id: int,
    user = Depends(get_current_user),
    db   = Depends(get_db),
):
    repo = PredictionRepo(db)
    job = repo.get(job_id)
    if job is None or job.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return job