import io, json
from typing import Any, Dict, List, Tuple
from aiogram import Bot, types

def _ext(name: str | None) -> str:
    if not name or "." not in name:
        return ""
    return name.rsplit(".", 1)[-1].lower()

def parse_json_bytes(b: bytes) -> List[Dict[str, Any]]:
    data = json.loads(b.decode("utf-8"))
    if isinstance(data, dict):
        # dict of columns -> lists OR single row
        if data and all(isinstance(v, list) for v in data.values()):
            rows: List[Dict[str, Any]] = []
            keys = list(data.keys())
            length = max(len(v) for v in data.values()) if data else 0
            for i in range(length):
                rows.append({k: (data[k][i] if i < len(data[k]) else None) for k in keys})
            return rows
        return [data]
    if isinstance(data, list):
        return data
    raise ValueError("Unsupported JSON structure")

async def parse_document(bot: Bot, doc: types.Document) -> Tuple[list[dict], str]:
    """
    Скачивает файл и парсит в список dict.
    Возвращает (rows, summary), где summary — короткая строка для ответа.
    """
    buf = io.BytesIO()
    await bot.download(doc, destination=buf)
    content = buf.getvalue()
    ext = _ext(doc.file_name)
    ctype = (doc.mime_type or "").lower()

    # CSV
    if ext == "csv" or "csv" in ctype:
        import csv
        text = content.decode("utf-8", errors="replace")
        rows = list(csv.DictReader(io.StringIO(text)))
        return rows, f"CSV rows: {len(rows)}"

    # JSON
    if ext == "json" or "json" in ctype:
        rows = parse_json_bytes(content)
        return rows, f"JSON rows: {len(rows)}"

    # XLSX
    if ext == "xlsx" or "spreadsheetml" in ctype:
        try:
            import pandas as pd
            rows = pd.read_excel(io.BytesIO(content)).to_dict(orient="records")
            return rows, f"XLSX rows: {len(rows)}"
        except Exception as e:
            raise ValueError(f"XLSX parsing error: {e}")

    # Parquet
    if ext in ("parquet", "pq") or "parquet" in ctype:
        try:
            import pandas as pd
            rows = pd.read_parquet(io.BytesIO(content)).to_dict(orient="records")
            return rows, f"Parquet rows: {len(rows)}"
        except Exception as e:
            raise ValueError(f"Parquet parsing error: {e}")

    raise ValueError(f"Unsupported file type: {doc.file_name or ctype}")