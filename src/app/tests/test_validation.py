import httpx


def test_mixed_rows_ok_with_invalid_list(
    api: httpx.Client, random_email, register_or_login, auth_headers, poll_job
):
    email = random_email("validmix")
    token = register_or_login(api, email)

    api.post("/account/top-up", headers=auth_headers(token), json={"amount": 200, "reason": "tests"})

    data = [
        {"date": "2025-05-01", "value": 1},
        {"date": "2025-05-02", "value": 2},
        {"date": "error",      "value": 2},  # некорректная дата
    ]
    submit = api.post("/predict/", headers=auth_headers(token),
                      json={"model_name": "Demo", "data": data})
    job_id = submit.json()["id"]

    job = poll_job(api, token, job_id)
    assert job["status"] == "OK"

    invalid_rows = job.get("invalid_rows")
    predictions = job.get("predictions")
    valid_rows = job.get("valid_input")
    assert len(predictions) == len(valid_rows)
    assert len(invalid_rows) > 0


def test_missing_time_or_price_results_in_error(
    api: httpx.Client, random_email, register_or_login, auth_headers, poll_job
):
    email = random_email("no_fields")
    token = register_or_login(api, email)

    api.post("/account/top-up", headers=auth_headers(token), json={"amount": 100, "reason": "tests"})

    # нет обязательного поля 'date'
    data_no_time = [{"f1": 5, "value": 1}, {"f1": 6, "value": 2}]
    submit1 = api.post("/predict/", headers=auth_headers(token),
                       json={"model_name": "Demo", "data": data_no_time})
    job1 = poll_job(api, token, submit1.json()["id"])
    assert job1["status"] == "ERROR"

    # нет обязательного поля цены
    data_no_price = [{"date": "2025-05-01", "error": 1}, {"date": "2025-05-02", "error": 2}]
    submit2 = api.post("/predict/", headers=auth_headers(token),
                       json={"model_name": "Demo", "data": data_no_price})
    job2 = poll_job(api, token, submit2.json()["id"])
    assert job2["status"] == "ERROR"


def test_invalid_payload_type_rejected(api: httpx.Client, random_email, register_or_login, auth_headers):
    email = random_email("badpayload")
    token = register_or_login(api, email)

    api.post("/account/top-up", headers=auth_headers(token), json={"amount": 50, "reason": "tests"})

    response = api.post("/predict/", headers=auth_headers(token),
                        json={"model_name": "Demo", "data": "oops"})
    assert response.status_code in (400, 422)