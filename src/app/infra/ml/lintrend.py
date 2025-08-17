from typing import List, Dict, Any
import numpy as np
from sklearn.linear_model import LinearRegression

from src.app.domain.ml_model import MLModel


class LinearTrend(MLModel):
    """
    Простая модель: оценивает линейный тренд y ~ a + b * t
    по последним наблюдениям и экстраполирует на N шагов вперёд.
    Использует только цену (price/value/target/close/y).
    """
    name = "LinearTrend"
    price_per_row = 2

    def predict(self, rows: List[Dict[str, Any]]) -> List[float]:
        # извлекаем последовательность цен
        y: List[float] = []
        for r in rows:
            for key in ("price", "value", "target", "close", "y"):
                v = r.get(key)
                if isinstance(v, (int, float)):
                    y.append(float(v))
                    break
            else:
                nums = [float(v) for v in r.values() if isinstance(v, (int, float))]
                if nums:
                    y.append(nums[0])

        n = len(y)
        if n == 0:
            return []

        # обучаем OLS
        X = np.arange(n).reshape(-1, 1)
        reg = LinearRegression()
        reg.fit(X, np.array(y, dtype=float))

        # прогноз на N шагов вперёд
        h = len(rows)
        X_future = np.arange(n, n + h).reshape(-1, 1)
        y_pred = reg.predict(X_future)
        return [float(v) for v in y_pred]