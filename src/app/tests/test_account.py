import httpx


def test_get_balance_initial_value(api: httpx.Client, random_email, register_or_login, auth_headers):
    email = random_email("acc")
    token = register_or_login(api, email)

    response = api.get("/account/balance", headers=auth_headers(token))
    assert response.status_code == 200
    assert "balance" in response.json()


def test_top_up_increases_balance(api: httpx.Client, random_email, register_or_login, auth_headers):
    email = random_email("topup")
    token = register_or_login(api, email)

    start = api.get("/account/balance", headers=auth_headers(token)).json()["balance"]

    amount = 123
    response = api.post("/account/top-up",
                        headers=auth_headers(token),
                        json={"amount": amount, "reason": "tests"})
    assert response.status_code == 201
    new_balance = response.json()["balance"]
    assert new_balance == start + amount


def test_transactions_history_contains_topup(api: httpx.Client, random_email, register_or_login, auth_headers):
    email = random_email("tx")
    token = register_or_login(api, email)

    amount = 77
    api.post("/account/top-up", headers=auth_headers(token), json={"amount": amount, "reason": "tests"})

    response = api.get("/account/transactions", headers=auth_headers(token))
    assert response.status_code == 200
    txs = response.json()
    assert isinstance(txs, list) and len(txs) >= 1
    last = txs[0]
    assert last["amount"] == amount
    assert "balance_after" in last


def test_top_up_negative_amount_rejected(api: httpx.Client, random_email, register_or_login, auth_headers):
    email = random_email("neg")
    token = register_or_login(api, email)

    response = api.post("/account/top-up",
                        headers=auth_headers(token),
                        json={"amount": -1, "reason": "tests"})
    assert response.status_code in (400, 422)