from fastapi import APIRouter, Depends, HTTPException, status
from src.app.api.schemas import PredictionIn, PredictionOut, PredictionShort
from src.app.api.deps import get_current_user, get_db
from src.app.infra.mq import rpc_predict
from src.app.infra.repositories import AccountRepo, PredictionRepo
from src.app.services.prediction_service import PredictionService
import os

router = APIRouter(prefix="/predict", tags=["Prediction"])

COST_PER_ROW = int(os.getenv("COST_PER_ROW"))

@router.post("/", response_model=PredictionOut, status_code=201)
async def predict(
    payload: PredictionIn,
    user = Depends(get_current_user),
    db   = Depends(get_db),
):
    est_cost = len(payload.data) * COST_PER_ROW
    balance = AccountRepo(db).load(user.account.id).balance
    if balance < est_cost:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "Not enough credits")

    # отправляем RPC-запрос воркеру
    result = await rpc_predict({
        "user_id":    user.id,
        "account_id": user.account.id,
        "model":      payload.model_name,
        "data":       payload.data,
    })

    if result.get("status") == "error":
        err = result.get("error", "Model inference failed")
        if err == "not_enough_credits":
            raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, err)
        if err == "rpc_timeout":
            raise HTTPException(status.HTTP_504_GATEWAY_TIMEOUT, "Worker timeout")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, err)

    return PredictionOut(**result)


@router.get("/history", response_model=list[PredictionShort])
def history(
    user = Depends(get_current_user),
    db   = Depends(get_db),
):
    svc = PredictionService(AccountRepo(db), PredictionRepo(db))
    return svc.history(user.id)