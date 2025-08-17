from typing import List, Dict, Any
import numpy as np
from src.app.domain.ml_model import MLModel

class DemoAR(MLModel):
    name = "Demo"
    price_per_row = 1

    def predict(self, rows: List[Dict[str, Any]]) -> List[float]:
        """
        rows — исторические точки, отсортированные по времени.
        Возвращаем n прогнозов вперёд, где n = len(rows).
        """
        n = len(rows)
        if n == 0:
            return []

        y_hist = [float(r["price"]) for r in rows if "price" in r]
        if len(y_hist) == 0:
            return []

        if len(y_hist) == 1:
            return [y_hist[-1]] * n

        y1, y2 = y_hist[:-1], y_hist[1:]
        mx, my = float(np.mean(y1)), float(np.mean(y2))
        denom = float(np.sum((np.array(y1) - mx) ** 2))

        if denom == 0.0:
            last = y_hist[-1]
            return [last] * n

        b = float(np.sum((np.array(y1) - mx) * (np.array(y2) - my)) / denom)
        a = my - b * mx

        preds: List[float] = []
        prev = y_hist[-1]
        for _ in range(n):
            nxt = a + b * prev
            preds.append(float(nxt))
            prev = nxt
        return preds