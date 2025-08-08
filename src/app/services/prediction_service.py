import os
from datetime import datetime, UTC
from typing import List, Dict, Any

from src.app.domain.enums import TxType, JobStatus
from src.app.domain.account import Account
from src.app.domain.prediction import PredictionJob
from src.app.domain.validation import Validator
from src.app.infra.repositories import AccountRepo, PredictionRepo

COST_PER_ROW: int = int(os.getenv("COST_PER_ROW"))


class PredictionService:
    """
    • валидирует данные
    • выполняет инференс
    • атомарно списывает средства и фиксирует PredictionJob
    """

    class NotEnoughCredits(Exception): ...
    class ModelError(Exception): ...

    def __init__(self, acc_repo: AccountRepo, pred_repo: PredictionRepo):
        self._acc_repo  = acc_repo
        self._pred_repo = pred_repo
        self._validator = Validator()

    # вызов модели (заглушка)
    def _run_model(self, name: str, rows: list[dict]) -> list[float]:
        try:
            # TODO: заменить на gRPC реальной модели
            return [0.0] * len(rows)
        except Exception as exc:
            raise PredictionService.ModelError(str(exc)) from exc

    def make_prediction(
        self,
        user,
        model_name: str,
        raw_rows: List[Dict[str, Any]],
    ) -> PredictionJob:

        res  = self._validator.validate(raw_rows)
        cost = len(res.valid_rows) * COST_PER_ROW

        acc: Account = self._acc_repo.load(user.account.id)
        if acc.balance < cost:
            raise PredictionService.NotEnoughCredits

        session = self._acc_repo.session

        with session.begin_nested():
            try:
                preds = self._run_model(model_name, res.valid_rows)

                acc.apply(
                    -cost,
                    f"Prediction {model_name}",
                    TxType.PREDICTION_CHARGE,
                )
                self._acc_repo.save(acc)

                job = PredictionJob(
                    owner_id     = user.id,
                    model_name   = model_name,
                    valid_input  = res.valid_rows,
                    predictions  = preds,
                    invalid_rows = res.invalid_rows,
                    cost         = cost,
                    status       = JobStatus.OK,
                    created_at   = datetime.now(UTC),
                )

            except PredictionService.ModelError as err:
                job = PredictionJob(
                    owner_id     = user.id,
                    model_name   = model_name,
                    valid_input  = res.valid_rows,
                    predictions  = [],
                    invalid_rows = res.invalid_rows,
                    cost         = 0,
                    status       = JobStatus.ERROR,
                    error        = str(err),
                    created_at   = datetime.now(UTC),
                )

            job = self._pred_repo.add(job)

        return job

    def history(self, user_id: int) -> list[PredictionJob]:
        return self._pred_repo.list_by_user(user_id)