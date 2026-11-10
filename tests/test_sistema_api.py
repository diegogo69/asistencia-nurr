import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
def admin_headers():
    res = client.post("/api/v1/auth/login", json={
        "documento_identidad": "v-00000000",
        "password": "admin1234"
    })
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_sistema_estado_sin_auth():
    res = client.get("/api/v1/sistema/estado")
    assert res.status_code == 401

def test_sistema_estado_admin(admin_headers):
    res = client.get("/api/v1/sistema/estado", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert "uptime_seconds" in data
    assert "logs_dir" in data
    assert data["https_enabled"] is True

def test_sistema_logs_admin(admin_headers):
    res = client.get("/api/v1/sistema/logs?lineas=20", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert "logs" in data
    assert "total_lineas" in data
    assert "logs_path" in data

def test_sistema_detener_sin_auth():
    res = client.post("/api/v1/sistema/detener")
    assert res.status_code == 401

@patch("app.api.v1.sistema.threading.Thread")
def test_sistema_detener_admin(mock_thread, admin_headers):
    res = client.post("/api/v1/sistema/detener", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "deteniendo"
    assert "detenido_por" in data
    assert mock_thread.called
