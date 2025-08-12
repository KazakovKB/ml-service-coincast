from typing import Sequence, Tuple, Any, Dict, List, Optional
from dataclasses import dataclass
import logging, math

logging.basicConfig(level=logging.INFO)

@dataclass()
class ValidationResult:
    valid_rows: List[Dict[str, Any]]
    invalid_rows: List[Tuple[int, Dict[str, Any]]]


class Validator:
    """Разделить валидные и ошибочные записи и нормализовать числовые поля."""

    # имена временной колонки (регистр игнорируем)
    TIME_KEYS = {"timestamp", "ts", "date", "datetime", "time"}

    @staticmethod
    def _maybe_float(v: Any) -> Optional[float]:
        """Пробует привести значение к float, возвращает None если нельзя или не конечное."""
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v) if math.isfinite(float(v)) else None
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return None
            if "," in s and "." not in s:
                s = s.replace(",", ".")
            try:
                x = float(s)
                return x if math.isfinite(x) else None
            except ValueError:
                return None
        return None

    @classmethod
    def validate(cls, raw: Sequence[Dict[str, Any]]) -> ValidationResult:
        valid_rows: List[Dict[str, Any]] = []
        invalid_rows: List[Tuple[int, Dict[str, Any]]] = []

        for idx, row in enumerate(raw):
            if not isinstance(row, dict):
                invalid_rows.append((idx, {"_error": "not a dict", "value": row}))
                continue

            # выделяем колонку времени
            time_key = next((k for k in row.keys() if k.lower() in cls.TIME_KEYS), None)

            normalized: Dict[str, Any] = {}
            if time_key is not None:
                normalized[time_key] = row[time_key]

            ok = True
            numeric_fields = 0

            for k, v in row.items():
                if k == time_key:
                    continue
                fv = cls._maybe_float(v)
                if fv is None:
                    ok = False
                    break
                normalized[k] = fv
                numeric_fields += 1

            # нужны хотя бы какие-то числовые признаки
            if ok and numeric_fields > 0:
                valid_rows.append(normalized)
            else:
                invalid_rows.append((idx, row))

        logging.info(
            "Validator: %d valid, %d invalid",
            len(valid_rows), len(invalid_rows)
        )
        return ValidationResult(valid_rows=valid_rows, invalid_rows=invalid_rows)