import httpx


def test_register_and_login_returns_token(api: httpx.Client, random_email, register_or_login):
    email = random_email("auth")
    token = register_or_login(api, email)
    assert isinstance(token, str) and len(token) > 10


def test_unauthorized_access_is_denied(api: httpx.Client):
    response = api.get("/account/balance")
    assert response.status_code in (401, 403)