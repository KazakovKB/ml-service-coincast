from abc import ABC, abstractmethod
from typing import Any, Dict, List, Sequence

class MLModel(ABC):
    """
    Доменный интерфейс ML-модели
    """

    name: str
    price_per_row: int = 1

    @abstractmethod
    def predict(self, rows: Sequence[Dict[str, Any]]) -> List[float]:
        """
        Вернуть предсказание для каждой переданной строки
        """
        ...


class SklearnModel(MLModel):
    """
    Универсальный адаптер для sklearn-совместимых моделей
    """

    def __init__(self, name: str, estimator: Any) -> None:
        self.name = name
        self._estimator = estimator

    def predict(self, rows: Sequence[Dict[str, Any]]) -> List[float]:
        X: List[List[float]] = []
        for row in rows:
            numeric_items = [(k, v) for k, v in row.items() if isinstance(v, (int, float))]
            numeric_items.sort(key=lambda kv: kv[0])
            X.append([float(v) for _, v in numeric_items])

        preds = self._estimator.predict(X)
        return [float(p) for p in preds]