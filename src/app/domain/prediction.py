from dataclasses import dataclass, field
from typing import Sequence, Any, Tuple
from datetime import datetime, UTC

@dataclass
class PredictionJob:
    user_id: int
    model_name: str
    valid_input: Sequence[Any]
    predictions: Sequence[Any]
    invalid_rows: Sequence[Tuple[int, Any]]
    cost: int
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))