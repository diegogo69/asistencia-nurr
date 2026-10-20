import uuid
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

def test_check_documento_uniqueness(auth_headers):
    # Cédula ya existente (admin)
    res_existing = client.get("/api/v1/usuarios/check-documento?documento=V-00000000", headers=auth_headers)
    assert res_existing.status_code == 200
    assert res_existing.json()["disponible"] is False

    # Cédula nueva
    random_doc = f"v-{uuid.uuid4().int % 90000000 + 10000000}"
    res_new = client.get(f"/api/v1/usuarios/check-documento?documento={random_doc}", headers=auth_headers)
    assert res_new.status_code == 200
    assert res_new.json()["disponible"] is True

def test_usuarios_crud_and_credentials(auth_headers):
    # 1. Obtener IDs maestros para rol y departamento
    dept_res = client.get("/api/v1/departamentos", headers=auth_headers)
    dept_id = dept_res.json()["items"][0]["id"]

    # Rol Técnico Contratado (id 3 o buscar por nombre)
    doc_nuevo = f"v-{uuid.uuid4().int % 90000000 + 10000000}"
    create_res = client.post("/api/v1/usuarios", json={
        "documento_identidad": doc_nuevo,
        "nombre": "Pedro",
        "apellido": "Alvarado",
        "rol_id": 3,  # Técnico Contratado (no requiere password)
        "departamento_id": dept_id,
        "activo": True
    }, headers=auth_headers)
    assert create_res.status_code == 201
    user_data = create_res.json()
    user_id = user_data["id"]
    assert user_data["documento_identidad"] == doc_nuevo
    assert user_data["codigo_qr"] is not None
    assert user_data["tiene_biometria"] is False

    # 2. Enrolamiento Biométrico con vector 128D (simulando face-api.js)
    mock_vector = [0.05 * (i % 10) for i in range(128)]
    enroll_res = client.post(f"/api/v1/usuarios/{user_id}/biometria", json={
        "vector": mock_vector
    }, headers=auth_headers)
    assert enroll_res.status_code == 200
    assert enroll_res.json()["tiene_biometria"] is True

    # 3. Regenerar Código QR
    old_qr = user_data["codigo_qr"]
    regen_res = client.post(f"/api/v1/usuarios/{user_id}/regenerar-qr", headers=auth_headers)
    assert regen_res.status_code == 200
    new_qr = regen_res.json()["codigo_qr"]
    assert new_qr != old_qr

    # 4. Descargar imagen del QR
    qr_img_res = client.get(f"/api/v1/usuarios/{user_id}/credencial-qr", headers=auth_headers)
    assert qr_img_res.status_code == 200
    assert qr_img_res.headers["content-type"] == "image/png"
    assert qr_img_res.content.startswith(b"\x89PNG")

    # 5. Descargar carnet en PDF
    pdf_res = client.get(f"/api/v1/usuarios/{user_id}/credencial-pdf", headers=auth_headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF")

    # 6. Borrado físico de usuario sin asistencias
    del_res = client.delete(f"/api/v1/usuarios/{user_id}", headers=auth_headers)
    assert del_res.status_code == 200
    assert del_res.json()["tipo_borrado"] == "fisico"

def test_usuarios_create_with_nombres_apellidos_aliases(auth_headers):
    dept_res = client.get("/api/v1/departamentos", headers=auth_headers)
    dept_id = dept_res.json()["items"][0]["id"]

    doc_nuevo = f"v-{uuid.uuid4().int % 90000000 + 10000000}"
    create_res = client.post("/api/v1/usuarios", json={
        "documento_identidad": doc_nuevo,
        "nombres": "Carlos",
        "apellidos": "Mendoza",
        "rol_id": 3,
        "departamento_id": dept_id,
        "horario_id": None,
        "activo": True
    }, headers=auth_headers)
    assert create_res.status_code == 201
    user_data = create_res.json()
    assert user_data["nombre"] == "Carlos"
    assert user_data["apellido"] == "Mendoza"
    assert user_data["nombres"] == "Carlos"
    assert user_data["apellidos"] == "Mendoza"
    assert user_data["nombre_completo"] == "Carlos Mendoza"

    # Cleanup
    client.delete(f"/api/v1/usuarios/{user_data['id']}", headers=auth_headers)

def test_usuarios_pagination_limit_up_to_500(auth_headers):
    # Probar que pedir limit=200 es completamente válido y no arroja 422
    res = client.get("/api/v1/usuarios?limit=200", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert data["limit"] == 200
