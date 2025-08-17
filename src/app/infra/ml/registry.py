from typing import Dict, Callable
from src.app.domain.ml_model import MLModel
from src.app.infra.ml.demo_ar import DemoAR
from src.app.infra.ml.lintrend import LinearTrend

_REGISTRY: Dict[str, Callable[[], MLModel]] = {
    "Demo": DemoAR,
    "LinearTrend": LinearTrend,
}

def get(name: str) -> MLModel:
    try:
        return _REGISTRY[name]()
    except KeyError:
        raise KeyError(f"Unknown model: {name}")

def list_names(allowed: list[str] | None = None) -> list[str]:
    names = list(_REGISTRY.keys())
    return [n for n in names if (allowed is None or n in allowed)]