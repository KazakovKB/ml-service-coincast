from abc import ABC, abstractmethod
from typing import Sequence, Any

class MLModel(ABC):
    """Абстракция ML-модели."""

    name: str
    price_per_row: int = 1

    @abstractmethod
    def predict(self, rows: Sequence[Any]) -> Sequence[Any]:
        """Возвращает предсказание для каждой строки?"""


class SklearnModel(MLModel):
    """Конкретная реализация."""

    def __init__(self, name: str, estimator: Any) -> None:
        self.name = name
        self.__estimator = estimator

    def predict(self, rows: Sequence[Any]) -> Sequence[Any]:
        return self.__estimator.predict(rows).tolist()