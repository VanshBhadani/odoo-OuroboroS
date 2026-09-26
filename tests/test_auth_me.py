from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_users_me_unauthorized():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}

def test_read_users_me_invalid_token():
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate credentials"}
