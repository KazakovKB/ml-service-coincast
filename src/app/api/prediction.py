from fastapi import APIRouter, Depends, HTTPException, status

from src.app.api.schemas import PredictionIn, PredictionOut, PredictionShort
from src.app.api.deps import get_current_user, get_db
from src.app.services.prediction_service import PredictionService
from src.app.infra.repositories import AccountRepo, PredictionRepo


router = APIRouter(prefix="/predict", tags=["Prediction"])


@router.post("/", response_model=PredictionOut, status_code=201)
def predict(
    payload: PredictionIn,
    user = Depends(get_current_user),
    db   = Depends(get_db),
):
    svc = PredictionService(AccountRepo(db), PredictionRepo(db))
    try:
        return svc.make_prediction(user, payload.model_name, payload.data)
    except PredictionService.NotEnoughCredits:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Not enough credits",
        )

@router.get("/history", response_model=list[PredictionShort])
def history(
    user = Depends(get_current_user),
    db   = Depends(get_db),
):
    svc = PredictionService(AccountRepo(db), PredictionRepo(db))
    return svc.history(user.id)