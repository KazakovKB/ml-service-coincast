import os
from typing import Any, Dict, List

import httpx


API_BASE = os.getenv("API_BASE")

class ApiError(Exception):
    """HTTP-ошибка для бота."""
    def __init__(self, status: int, detail: str = ""):
        super().__init__(detail or str(status))
        self.status = status
        self.detail = detail


class ApiClient:
    """
    обёртка над FastAPI-REST.
    """

    def __init__(self) -> None:
        self._token: str | None = None
        self._http = httpx.AsyncClient(base_url=API_BASE, timeout=10.0)

    async def _request(self, method: str, url: str, **kw) -> Any:
        if self._token:
            kw.setdefault("headers", {})["Authorization"] = f"Bearer {self._token}"

        try:
            resp = await self._http.request(method, url, **kw)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            try:
                detail = e.response.json().get("detail", "")
            except Exception:
                detail = e.response.text
            raise ApiError(e.response.status_code, detail) from None

    async def register(self, email: str, password: str) -> bool:
        data = await self._request("POST", "/auth/register",
                                   json={"email": email, "password": password})
        self._token = data["access_token"]
        return True

    async def login(self, email: str, password: str) -> None:
        data = await self._request("POST", "/auth/login",
                                   data={"username": email, "password": password})
        self._token = data["access_token"]

    async def balance(self) -> int:
        data = await self._request("GET", "/account/balance")
        return data["balance"]

    async def topup(self, amount: int, reason: str) -> int:
        data = await self._request("POST", "/account/top-up",
                                   json={"amount": amount, "reason": reason})
        return data["balance"]

    async def transactions(self) -> List[Dict]:
        return await self._request("GET", "/account/transactions")

    async def predict(self, model: str, rows: list[dict]) -> Dict:
        return await self._request("POST", "/predict/",
                                   json={"model_name": model, "data": rows})

    async def pred_history(self) -> List[Dict]:
        return await self._request("GET", "/predict/history")

    async def pred_job(self, job_id: int) -> Dict:
        return await self._request("GET", f"/predict/{job_id}")