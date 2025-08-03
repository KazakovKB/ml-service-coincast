from dataclasses import dataclass, field
from typing import Sequence, Any, Tuple
from datetime import datetime, UTC


@dataclass
class PredictionJob:
    owner_id: int
    model_name: str
    valid_input: Sequence[Any]
    predictions: Sequence[Any]
    invalid_rows: Sequence[Tuple[int, Any]]
    cost: int
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: int | None = None

    def n_valid(self) -> int:
        return len(self.valid_input)

    def n_invalid(self) -> int:
        return len(self.invalid_rows)

    def summary(self) -> dict:
        return {
            "model": self.model_name,
            "total_rows": self.n_valid() + self.n_invalid(),
            "predicted": self.n_valid(),
            "invalid": self.n_invalid(),
            "cost": self.cost,
            "timestamp": self.created_at.isoformat(),
        }

    def get_invalid_rows_for_user(self) -> list:
        return [row for idx, row in self.invalid_rows]