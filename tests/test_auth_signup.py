from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_signup_missing_fields():
    response = client.post("/api/v1/auth/signup", json={"email": "new@email.com"})
    # Pydantic should catch missing name and password
    assert response.status_code == 422

def test_signup_invalid_email():
    response = client.post("/api/v1/auth/signup", json={
        "email": "not-an-email",
        "name": "Test User",
        "password": "Password123"
    })
    # Pydantic EmailStr validation
    assert response.status_code == 422
