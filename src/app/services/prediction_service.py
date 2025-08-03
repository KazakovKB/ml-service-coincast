from datetime import datetime, UTC
from typing import List, Dict, Any

from src.app.domain.account import Account
from src.app.domain.enums import TxType
from src.app.domain.prediction import PredictionJob
from src.app.domain.validation import Validator
from src.app.infra.repositories import AccountRepo, PredictionRepo

import os

COST_PER_ROW = os.getenv('COST_PER_ROW')

class PredictionService:
    """
    - валидирует входные данные
    - вызывает ML-модель (заглушка)
    - списывает кредиты
    - сохраняет PredictionJob в БД через PredictionRepo
    """

    class NotEnoughCredits(Exception): ...

    def __init__(self, acc_repo: AccountRepo, pred_repo: PredictionRepo):
        self._acc_repo = acc_repo
        self._pred_repo = pred_repo
        self._validator = Validator()

    def make_prediction(
        self,
        user,
        model_name: str,
        raw_rows: List[Dict[str, Any]],
    ) -> PredictionJob:

        # валидация
        res = self._validator.validate(raw_rows)

        # стоимость
        cost = int(len(res.valid_rows) * COST_PER_ROW)
        if user.account.balance < cost:
            raise PredictionService.NotEnoughCredits

        # «предсказание» (заглушка)
        preds = [0.0] * len(res.valid_rows)

        # списываем средства
        acc: Account = self._acc_repo.load(user.account.id)
        acc.apply(-cost, f"Prediction {model_name}", TxType.PREDICTION_CHARGE)
        self._acc_repo.save(acc)

        # сохраняем PredictionJob
        job = PredictionJob(
            owner_id=user.id,
            model_name=model_name,
            valid_input=res.valid_rows,
            predictions=preds,
            invalid_rows=res.invalid_rows,
            cost=cost,
            created_at=datetime.now(UTC),
        )
        return self._pred_repo.add(job)

    def history(self, user_id: int) -> list[PredictionJob]:
        """Список всех PredictionJob пользователя."""
        return self._pred_repo.list_by_user(user_id)