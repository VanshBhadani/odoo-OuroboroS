from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_login_invalid_credentials():
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "fake@stocksense.local", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password"}

def test_login_missing_password():
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "admin@stocksense.local"},
    )
    assert response.status_code == 422
