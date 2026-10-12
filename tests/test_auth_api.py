from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_login_success():
    response = client.post("/api/v1/auth/login", json={
        "documento_identidad": "V-00000000",
        "password": "admin1234"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["documento_identidad"] == "V-00000000"
    assert data["user"]["rol"] == "Coordinador"
    assert data["user"]["requiere_password"] is True

def test_login_invalid_password():
    response = client.post("/api/v1/auth/login", json={
        "documento_identidad": "V-00000000",
        "password": "clave_incorrecta"
    })
    assert response.status_code == 401
    assert "inválidas" in response.json()["detail"]

def test_login_nonexistent_user():
    response = client.post("/api/v1/auth/login", json={
        "documento_identidad": "V-99999999",
        "password": "admin"
    })
    assert response.status_code == 401

def test_auth_me_and_logout():
    # 1. Login
    login_res = client.post("/api/v1/auth/login", json={
        "documento_identidad": "V-00000000",
        "password": "admin1234"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get me
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["documento_identidad"] == "V-00000000"

    # 3. Logout
    logout_res = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 200

def test_auth_me_unauthorized():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
