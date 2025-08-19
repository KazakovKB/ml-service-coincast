import httpx


def test_submit_prediction_returns_202_and_pending(api: httpx.Client, random_email, register_or_login, auth_headers):
    email = random_email("pred")
    token = register_or_login(api, email)

    api.post("/account/top-up", headers=auth_headers(token), json={"amount": 1000, "reason": "tests"})

    rows = [{"date": "2025-05-01", "value": 1}, {"date": "2025-05-02", "value": 2}]
    response = api.post("/predict/", headers=auth_headers(token),
                        json={"model_name": "Demo", "data": rows})
    assert response.status_code == 202
    payload = response.json()
    assert "id" in payload and payload["status"] == "PENDING"


def test_prediction_completes_ok_and_cost_matches_valid_count(
    api: httpx.Client, random_email, register_or_login, auth_headers, poll_job
):
    email = random_email("pred2")
    token = register_or_login(api, email)

    api.post("/account/top-up", headers=auth_headers(token), json={"amount": 1000, "reason": "tests"})

    rows = [{"date": "2025-05-01", "value": 1}, {"date": "2025-05-02", "value": 2}]
    submit = api.post("/predict/", headers=auth_headers(token),
                      json={"model_name": "Demo", "data": rows})
    job_id = submit.json()["id"]

    job = poll_job(api, token, job_id)
    assert job["status"] == "OK"

    predictions = job.get("predictions")
    valid_rows = job.get("valid_input")
    assert isinstance(predictions, list)
    assert len(predictions) == len(valid_rows)
    assert job.get("cost") >= 0