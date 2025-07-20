from typing import Protocol, Sequence, Tuple, Any, Dict, List


class ValidationResult(Protocol):
    valid_rows: List[Any]
    invalid_rows: List[Tuple[int, Any]]
    ...


class Validator:
    """Разделяет валидные и ошибочные записи."""
    def validate(self, raw: Sequence[Dict[str, Any]]) -> ValidationResult:
        ...