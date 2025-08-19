import uuid
import httpx


def test_user_cannot_read_other_users_job(
    api: httpx.Client, register_or_login, auth_headers
):
    # User A создаёт задачу
    token_a = register_or_login(api, f"a_{uuid.uuid4().hex[:6]}@t.local")
    api.post("/account/top-up", headers=auth_headers(token_a), json={"amount": 100, "reason": "tests"})

    submit = api.post("/predict/", headers=auth_headers(token_a),
                      json={"model_name": "Demo", "data": [{"date": "2025-05-03", "value": 2}]})
    job_id = submit.json()["id"]

    # User B пытается прочитать джобу A
    token_b = register_or_login(api, f"b_{uuid.uuid4().hex[:6]}@t.local")
    response = api.get(f"/predict/{job_id}", headers=auth_headers(token_b))
    assert response.status_code == 404