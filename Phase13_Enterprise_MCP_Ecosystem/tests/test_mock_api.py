from starlette.testclient import TestClient

from enterprise_mcp.mock_enterprise.app import USED_TOKEN_IDS, app


def test_mock_api_enforces_token_then_single_api_call() -> None:
    USED_TOKEN_IDS.clear()
    client = TestClient(app)
    token_response = client.post(
        "/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "work-item-local",
            "client_secret": "fictional-work-item-secret",
            "scope": "work-item.read",
            "audience": "internal-api-gateway",
        },
    )
    assert token_response.status_code == 200
    access_token = token_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    assert client.get("/participants/P-DEMO-001", headers=headers).status_code == 200
    assert client.get("/participants/P-DEMO-001", headers=headers).status_code == 401
