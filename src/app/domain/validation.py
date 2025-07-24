from typing import Sequence, Tuple, Any, Dict, List
from dataclasses import dataclass


@dataclass()
class ValidationResult:
    valid_rows: List[Any]
    invalid_rows: List[Tuple[int, Any]]


class Validator:
    """Разделяет валидные и ошибочные записи."""

    @staticmethod
    def validate(raw: Sequence[Dict[str, Any]]) -> ValidationResult:
        valid_rows = []
        invalid_rows = []
        for idx, row in enumerate(raw):
            # Все значения присутствуют и являются числами
            if all(
                v is not None and isinstance(v, (int, float))
                for v in row.values()
            ):
                valid_rows.append(row)
            else:
                invalid_rows.append((idx, row))

        return ValidationResult(valid_rows=valid_rows, invalid_rows=invalid_rows)