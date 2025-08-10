import os
from typing import List, Dict, Any

from src.app.domain.enums import TxType
from src.app.domain.account import Account
from src.app.domain.prediction import PredictionJob
from src.app.domain.validation import Validator
from src.app.infra.repositories import AccountRepo, PredictionRepo

COST_PER_ROW: int = int(os.getenv("COST_PER_ROW"))


class PredictionService:

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
        """Списание средств + фиксация успешного результата в рамках одной транзакции."""
        cost = len(valid_rows) * COST_PER_ROW

        acc: Account = self._acc_repo.load(account_id)
        if acc.balance < cost:
            # помечаем джобу как ошибочную
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

        # валидация
        res = self._validator.validate(raw_rows)

        # создаём pending-запись сразу, чтобы всегда была история
        pending = self._pred_repo.create_pending(owner_id=user.id, model_name=model_name)

        session = self._acc_repo.session
        with session.begin_nested():
            try:
                preds = self._run_model(model_name, res.valid_rows)

                # списание + успешное завершение
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

    def process_job(
        self,
        *,
        job_id: int,
        account_id: int,
        model_name: str,
        raw_rows: List[Dict[str, Any]],
    ) -> PredictionJob:
        """
        Вызывается воркером: получает job_id и данные, валидирует, инференсит,
        списывает и помечает job OK/ERROR.
        """
        res = self._validator.validate(raw_rows)

        session = self._acc_repo.session
        with session.begin_nested():
            try:
                preds = self._run_model(model_name, res.valid_rows)

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

    def history(self, user_id: int) -> list[PredictionJob]:
        return self._pred_repo.list_by_user(user_id)