import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
def auth_headers():
    login_res = client.post("/api/v1/auth/login", json={
        "documento_identidad": "V-00000000",
        "password": "admin1234"
    })
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_historial_api(auth_headers):
    res = client.get("/api/v1/asistencias/historial", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert data["page"] == 1

def test_reporte_resumen_api(auth_headers):
    res = client.get("/api/v1/reportes/resumen", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_marcaciones" in data
    assert "total_horas_acumuladas" in data
    assert "usuarios" in data

def test_exportar_csv_api(auth_headers):
    res = client.get("/api/v1/reportes/exportar/csv", headers=auth_headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "attachment" in res.headers["content-disposition"]
    # Verificar UTF-8 BOM
    assert res.content.startswith(b"\xef\xbb\xbf")

def test_exportar_pdf_api(auth_headers):
    res = client.get("/api/v1/reportes/exportar/pdf", headers=auth_headers)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "inline" in res.headers["content-disposition"]
    # Verificar firma %PDF
    assert res.content.startswith(b"%PDF")
