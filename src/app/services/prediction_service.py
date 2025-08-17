import os
from typing import List, Dict, Any

from src.app.domain.enums import TxType
from src.app.domain.account import Account
from src.app.domain.prediction import PredictionJob
from src.app.domain.validation import Validator
from src.app.infra.repositories import AccountRepo, PredictionRepo
from src.app.services.model_gateway import ModelGateway

COST_PER_ROW: int = int(os.getenv("COST_PER_ROW"))


class PredictionService:

    class NotEnoughCredits(Exception): ...
    class ModelError(Exception): ...

    def __init__(self, acc_repo: AccountRepo, pred_repo: PredictionRepo, model_gateway: ModelGateway | None = None):
        self._acc_repo  = acc_repo
        self._pred_repo = pred_repo
        self._validator = Validator()
        self._models = model_gateway or ModelGateway()

    def _run_model(self, name: str, rows: list[dict]) -> list[float]:
        try:
            return self._models.predict(name, rows)
        except Exception as exc:
            raise PredictionService.ModelError(str(exc)) from exc

    def create_pending_job(self, *, owner_id: int, model_name: str) -> PredictionJob:
        return self._pred_repo.create_pending(owner_id=owner_id, model_name=model_name)

    def _charge_and_save_ok(
        self,
        *,
        account_id: int,
        job_id: int,
        model_name: str,
        valid_rows: List[Dict[str, Any]],
        invalid_rows: List[Dict[str, Any]],
        predictions: List[float],
    ) -> None:
        cost = len(valid_rows) * COST_PER_ROW

        acc: Account = self._acc_repo.load(account_id)
        if acc.balance < cost:
            self._pred_repo.mark_error(job_id, "not_enough_credits")
            raise PredictionService.NotEnoughCredits

        if cost > 0:
            acc.apply(-cost, f"Prediction {model_name}", TxType.PREDICTION_CHARGE)
            self._acc_repo.save(acc)

        self._pred_repo.mark_ok(
            job_id=job_id,
            predictions=predictions,
            cost=cost,
            valid_input=valid_rows,
            invalid_rows=invalid_rows,
        )

    def make_prediction(
        self,
        user,
        model_name: str,
        raw_rows: List[Dict[str, Any]],
    ) -> PredictionJob:
        """
        валидируем, создаём pending,
        если валидных строк нет — помечаем ошибкой; иначе считаем, списываем, сохраняем OK.
        """
        res = self._validator.validate(raw_rows)

        # создаём pending-запись сразу, чтобы всегда была история
        pending = self._pred_repo.create_pending(owner_id=user.id, model_name=model_name)

        # Жёсткое требование: dataset должен содержать колонку времени и цену
        if not res.valid_rows:
            self._pred_repo.mark_error(
                pending.id,
                "no_valid_rows: dataset must contain a time (date/datetime) and a numeric price"
            )
            return self._pred_repo.get(pending.id)

        session = self._acc_repo.session
        with session.begin_nested():
            try:
                preds = self._run_model(model_name, res.valid_rows)
                if len(preds) != len(res.valid_rows):
                    raise PredictionService.ModelError("Model returned wrong number of predictions")

                self._charge_and_save_ok(
                    account_id=user.account.id,
                    job_id=pending.id,
                    model_name=model_name,
                    valid_rows=res.valid_rows,
                    invalid_rows=res.invalid_rows,
                    predictions=preds,
                )
            except PredictionService.ModelError as err:
                self._pred_repo.mark_error(pending.id, str(err))

        return self._pred_repo.get(pending.id)

    def process_existing_job(
        self,
        *,
        job_id: int,
        account_id: int,
        model_name: str,
        raw_rows: List[Dict[str, Any]],
    ) -> PredictionJob:
        """
        Воркер: валидирует вход, при отсутствии валидных строк помечает ошибкой,
        иначе делает инференс, списывает и помечает job OK/ERROR.
        """
        res = self._validator.validate(raw_rows)

        # Жёсткое требование: time+price обязательны
        if not res.valid_rows:
            self._pred_repo.mark_error(
                job_id,
                "no_valid_rows: dataset must contain a time (date/datetime) and a numeric price"
            )
            return self._pred_repo.get(job_id)

        session = self._acc_repo.session
        with session.begin_nested():
            try:
                preds = self._run_model(model_name, res.valid_rows)
                if len(preds) != len(res.valid_rows):
                    raise PredictionService.ModelError("Model returned wrong number of predictions")

                self._charge_and_save_ok(
                    account_id=account_id,
                    job_id=job_id,
                    model_name=model_name,
                    valid_rows=res.valid_rows,
                    invalid_rows=res.invalid_rows,
                    predictions=preds,
                )
            except PredictionService.NotEnoughCredits:
                raise
            except PredictionService.ModelError as err:
                self._pred_repo.mark_error(job_id, str(err))

        return self._pred_repo.get(job_id)

    process_job = process_existing_job

    def history(self, user_id: int) -> list[PredictionJob]:
        return self._pred_repo.list_by_user(user_id)