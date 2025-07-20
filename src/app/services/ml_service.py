from src.app.domain.ml_model import MLModel
from src.app.domain.prediction import PredictionJob
from src.app.domain.user import Client
from src.app.domain.validation import Validator
from typing import Sequence, Dict, Any

class MLService:
    """Точка входа для REST контроллеров / FastAPI endpoints..."""

    def __init__(self, model_registry: dict[str, MLModel]) -> None:
        self.__models = model_registry
        self.__jobs: list[PredictionJob] = []

    # API

    def run_prediction(
        self,
        user: Client,
        model_name: str,
        dataset: Sequence[Dict[str, Any]],
        validator: Validator,
    ) -> PredictionJob:
        """Проверка баланса, валидация, списание кредитов, вызов модели."""
        if model_name not in self.__models:
            raise KeyError(f"Unknown model {model_name}")

        vr = validator.validate(dataset)
        price = len(vr.valid_rows) * self.__models[model_name].price_per_row

        # проверка средств
        user.pay_for_prediction(price, f"Prediction using {model_name}")

        # предсказание
        predictions = self.__models[model_name].predict(vr.valid_rows)

        job = PredictionJob(
            user_id=user.id,
            model_name=model_name,
            valid_input=vr.valid_rows,
            predictions=predictions,
            invalid_rows=vr.invalid_rows,
            cost=price,
        )
        self.__jobs.append(job)
        return job