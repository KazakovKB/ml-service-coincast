import os, time, uuid, httpx, pytest

API_BASE = os.getenv("API_BASE")

def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

def _wait_api_ready(timeout: float = 90.0) -> None:
    """Ждём пока API оживёт, проверяем /models/."""
    deadline = time.time() + timeout
    last_err = None
    with httpx.Client(base_url=API_BASE, timeout=5.0) as c:
        while time.time() < deadline:
            try:
                r = c.get("/models/")
                if r.status_code == 200:
                    return
                last_err = f"/models/ -> {r.status_code}"
            except Exception as e:
                last_err = e
            time.sleep(1.0)
    raise RuntimeError(f"API not ready: {last_err}")

@pytest.fixture(scope="session", autouse=True)
def _ensure_ready():
    _wait_api_ready()

@pytest.fixture
def client():
    with httpx.Client(base_url=API_BASE, timeout=10.0) as c:
        yield c

def _register_or_login(c: httpx.Client, email: str, password: str = "pass1234") -> str:
    r = c.post("/auth/register", json={"email": email, "password": password})
    if r.status_code in (200, 201):
        return r.json()["access_token"]
    r = c.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]

def _poll_job(c: httpx.Client, token: str, job_id: int, timeout: float = 40.0, interval: float = 0.5) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = c.get(f"/predict/{job_id}", headers=_auth(token))
        if r.status_code == 200:
            job = r.json()
            if job.get("status") in ("OK", "ERROR"):
                return job
        time.sleep(interval)
    raise AssertionError("Job did not finish in time")

def test_auth_endpoints_and_unauthorized(client: httpx.Client):
    email = f"user_{uuid.uuid4().hex[:8]}@test.local"
    token = _register_or_login(client, email)

    r = client.get("/account/balance", headers=_auth(token))
    assert r.status_code == 200
    assert "balance" in r.json()

    r = client.get("/account/balance")
    assert r.status_code in (401, 403)

def test_models_balance_top_up_transactions(client: httpx.Client):
    email = f"user_{uuid.uuid4().hex[:8]}@test.local"
    token = _register_or_login(client, email)

    r = client.get("/models/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    r = client.get("/account/balance", headers=_auth(token))
    assert r.status_code == 200
    start_bal = r.json()["balance"]

    topup = 123
    r = client.post("/account/top-up", headers=_auth(token), json={"amount": topup, "reason": "tests"})
    assert r.status_code == 201
    new_bal = r.json()["balance"]
    assert new_bal == start_bal + topup

    r = client.get("/account/transactions", headers=_auth(token))
    assert r.status_code == 200
    txs = r.json()
    assert isinstance(txs, list) and len(txs) >= 1
    last = txs[0]
    assert last["amount"] == topup
    assert last["balance_after"] == new_bal

def test_prediction_flow(client: httpx.Client):

    email = f"user_{uuid.uuid4().hex[:8]}@test.local"
    token = _register_or_login(client, email)

    r = client.post("/account/top-up", headers=_auth(token), json={"amount": 1000, "reason": "tests"})
    assert r.status_code == 201

    rows = [{"date": "2025-05-01", "value": 1}, {"date": "2025-05-02", "value": 2}]
    r = client.post("/predict/", headers=_auth(token), json={"model_name": "Demo", "data": rows})
    assert r.status_code == 202, r.text

    job_short = r.json()
    assert "id" in job_short

    job_id = job_short["id"]
    job = _poll_job(client, token, job_id)
    assert job["status"] == "OK"

    preds = job.get("predictions")
    assert isinstance(preds, list)

    valid_cnt = len(job.get("valid_input"))
    assert len(preds) == valid_cnt
    assert job.get("cost") >= 0

def test_validation_and_edge_cases(client: httpx.Client):
    email = f"user_{uuid.uuid4().hex[:8]}@test.local"
    token = _register_or_login(client, email)

    client.post("/account/top-up", headers=_auth(token), json={"amount": 200, "reason": "tests"})

    data = [{"date": "2025-05-01", "value": 1}, {"date": "2025-05-02", "value": 2}, {"date": "error", "value": 2}]
    r = client.post("/predict/", headers=_auth(token), json={"model_name": "Demo", "data": data})
    assert r.status_code == 202
    job_id = r.json()["id"]

    job = _poll_job(client, token, job_id)
    assert job["status"] == "OK"

    invalid = job.get("invalid_rows")
    preds   = job.get("predictions")
    vrows   = job.get("valid_input")
    assert len(preds) == len(vrows)
    assert len(invalid) > 0

    # Проверка валидации поля date/datetime
    data = [{"f1": 5, "value": 1}, {"f1": 6, "value": 2}, {"f1": 8, "value": 2}]
    r = client.post("/predict/", headers=_auth(token), json={"model_name": "Demo", "data": data})
    assert r.status_code == 202
    job_id = r.json()["id"]

    job = _poll_job(client, token, job_id)
    assert job["status"] == "ERROR"

    # Проверка валидации поля price
    data = [{"date": "2025-05-01", "error_name": 1},
            {"date": "2025-05-02", "error_name": 2},
            {"date": "2025-05-03", "error_name": 2}]
    r = client.post("/predict/", headers=_auth(token), json={"model_name": "Demo", "data": data})
    assert r.status_code == 202
    job_id = r.json()["id"]

    job = _poll_job(client, token, job_id)
    assert job["status"] == "ERROR"

def test_cannot_read_someone_else_job(client: httpx.Client):
    token_a = _register_or_login(client, f"a_{uuid.uuid4().hex[:6]}@t.local")
    client.post("/account/top-up", headers=_auth(token_a), json={"amount": 100, "reason": "tests"})
    r = client.post("/predict/", headers=_auth(token_a),
                    json={"model_name": "Demo", "data": [{"date":"2025-05-03","value":2}]})
    assert r.status_code == 202
    job_id = r.json()["id"]

    token_b = _register_or_login(client, f"b_{uuid.uuid4().hex[:6]}@t.local")
    r = client.get(f"/predict/{job_id}", headers=_auth(token_b))
    assert r.status_code == 404

def test_top_up_negative_amount(client: httpx.Client):
    token = _register_or_login(client, f"neg_{uuid.uuid4().hex[:6]}@t.local")
    r = client.post("/account/top-up", headers=_auth(token), json={"amount": -1, "reason": "tests"})
    assert r.status_code in (400, 422)

def test_predict_invalid_payload_structure(client: httpx.Client):
    token = _register_or_login(client, f"inv_{uuid.uuid4().hex[:6]}@t.local")
    client.post("/account/top-up", headers=_auth(token), json={"amount": 50, "reason": "tests"})

    r = client.post("/predict/", headers=_auth(token), json={"model_name": "Demo", "data": "oops"})
    assert r.status_code in (400, 422)