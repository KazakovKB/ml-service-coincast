from typing import Any, Dict, List, Optional
from src.app.infra.ml.registry import get as get_model, list_names

class ModelGateway:
    class UnknownModel(Exception):
        ...

    def predict(self, model_name: str, rows: List[Dict[str, Any]]) -> List[float]:
        try:
            model = get_model(model_name)
        except KeyError as e:
            raise ModelGateway.UnknownModel(str(e)) from e
        return model.predict(rows)

    def list_models(self, allowed: Optional[List[str]] = None) -> List[str]:
        return list_names(allowed)

    def price_per_row(self, model_name: str) -> int:
        return get_model(model_name).price_per_row