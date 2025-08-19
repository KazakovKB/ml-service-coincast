import httpx


def test_list_models_returns_array(api: httpx.Client):
    response = api.get("/models/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)