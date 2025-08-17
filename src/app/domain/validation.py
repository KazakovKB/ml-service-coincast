from typing import Sequence, Tuple, Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, UTC
import logging, math, re

logging.basicConfig(level=logging.INFO)

@dataclass()
class ValidationResult:
    valid_rows: List[Dict[str, Any]]
    invalid_rows: List[Tuple[int, Dict[str, Any]]]


class Validator:
    """Требует time+price, нормализует в {timestamp, price}, сортирует по времени."""

    # допустимые имена временной колонки (без учёта регистра)
    TIME_KEYS = {"timestamp", "ts", "date", "datetime", "time"}
    # допустимые имена цены (без учёта регистра)
    PRICE_KEYS = {"price", "value", "target", "close", "y"}
    _THOUSANDS_RE = re.compile(r"[ _]")

    @staticmethod
    def _parse_dt(v: Any) -> Optional[datetime]:
        if v is None:
            return None
        if isinstance(v, (int, float)):  # unix epoch seconds
            try:
                return datetime.fromtimestamp(float(v), UTC)
            except Exception:
                return None
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return None
            for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f",):
                try:
                    return datetime.fromisoformat(s) if "T" in s or "-" in s else datetime.strptime(s, fmt)
                except Exception:
                    pass
            try:
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            except Exception:
                return None
        return None

    @classmethod
    def _maybe_float(cls, v: Any) -> Optional[float]:
        if v is None:
            return None
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            try:
                x = float(v)
                return x if math.isfinite(x) else None
            except Exception:
                return None
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return None
            s = cls._THOUSANDS_RE.sub("", s)
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
                invalid_rows.append((idx, {"_error": "not_a_dict", "value": row}))
                continue

            # ищем ключи времени/цены
            time_key  = next((k for k in row.keys() if k.lower() in cls.TIME_KEYS), None)
            price_key = next((k for k in row.keys() if k.lower() in cls.PRICE_KEYS), None)

            if time_key is None:
                invalid_rows.append((idx, {"_error": "missing_time", **row}))
                continue
            if price_key is None:
                invalid_rows.append((idx, {"_error": "missing_price", **row}))
                continue

            dt = cls._parse_dt(row.get(time_key))
            if dt is None:
                invalid_rows.append((idx, {"_error": "bad_time", **row}))
                continue

            price = cls._maybe_float(row.get(price_key))
            if price is None:
                invalid_rows.append((idx, {"_error": "bad_price", **row}))
                continue

            valid_rows.append({"timestamp": dt.isoformat(), "price": float(price)})

        # сортировка по времени
        valid_rows.sort(key=lambda r: r["timestamp"])

        logging.info("Validator: %d valid, %d invalid", len(valid_rows), len(invalid_rows))
        return ValidationResult(valid_rows=valid_rows, invalid_rows=invalid_rows)