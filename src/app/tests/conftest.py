import os
import time
import uuid
import pytest
import httpx

API_BASE = os.getenv("API_BASE")


def _wait_api_ready(timeout: float = 90.0) -> None:
    """Ждём, пока API станет доступен: /models/ должен вернуть 200."""
    deadline = time.time() + timeout
    last_err = None
    with httpx.Client(base_url=API_BASE, timeout=5.0) as client:
        while time.time() < deadline:
            try:
                response = client.get("/models/")
                if response.status_code == 200:
                    return
                last_err = f"/models/ -> {response.status_code}"
            except Exception as e:
                last_err = e
            time.sleep(1.0)
    raise RuntimeError(f"API not ready: {last_err}")


@pytest.fixture(scope="session", autouse=True)
def ensure_api_is_ready():
    _wait_api_ready()


@pytest.fixture
def api() -> httpx.Client:
    """HTTP-клиент к API."""
    with httpx.Client(base_url=API_BASE, timeout=10.0) as client:
        yield client


@pytest.fixture
def auth_headers():
    """Фикстура-генератор заголовка Authorization."""
    def _make(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}
    return _make


@pytest.fixture
def random_email():
    """Генерирует уникальный e-mail."""
    def _make(prefix: str = "user") -> str:
        return f"{prefix}_{uuid.uuid4().hex[:8]}@test.local"
    return _make


@pytest.fixture
def register_or_login():
    """Возвращает функцию, которая регистрирует пользователя или логинит, и отдаёт токен."""
    def _call(api: httpx.Client, email: str, password: str = "pass1234") -> str:
        response = api.post("/auth/register", json={"email": email, "password": password})
        if response.status_code in (200, 201):
            return response.json()["access_token"]

        response = api.post("/auth/login", data={"username": email, "password": password})
        assert response.status_code == 200, response.text
        return response.json()["access_token"]
    return _call


@pytest.fixture
def poll_job(auth_headers):
    """Возвращает функцию ожидания завершения джобы предсказания."""
    def _call(api: httpx.Client, token: str, job_id: int,
              timeout: float = 40.0, interval: float = 0.5) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            response = api.get(f"/predict/{job_id}", headers=auth_headers(token))
            if response.status_code == 200:
                job = response.json()
                if job.get("status") in ("OK", "ERROR"):
                    return job
            time.sleep(interval)
        raise AssertionError("Job did not finish in time")
    return _call