from fastapi import APIRouter, Depends, HTTPException, status

from src.app.api.schemas import PredictionIn, PredictionOut, PredictionShort
from src.app.api.deps import get_current_user, get_db
from src.app.infra.mq import rpc_call
from src.app.services.prediction_service import PredictionService
from src.app.infra.repositories import AccountRepo, PredictionRepo


router = APIRouter(prefix="/predict", tags=["Prediction"])

@router.post("/", response_model=PredictionOut, status_code=201)
async def predict(
    payload: PredictionIn,
    user = Depends(get_current_user),
):
    # отправляем задачу и ждём ответ
    result = await rpc_call(
        {
            "user_id":    user.id,
            "account_id": user.account.id,
            "model":      payload.model_name,
            "data":       payload.data,
        }
    )

    # обработка ошибок
    if result.get("status") == "error":
        detail = result.get("error", "Model inference failed")
        if detail == "not_enough_credits":
            raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, detail)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail)

    return result


@router.get("/history", response_model=list[PredictionShort])
def history(
    user = Depends(get_current_user),
    db   = Depends(get_db),
):
    svc = PredictionService(AccountRepo(db), PredictionRepo(db))
    return svc.history(user.id)