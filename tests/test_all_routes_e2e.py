"""Batería de pruebas End-to-End que cubre la totalidad de las 40 rutas de la API de Asistencia-NURR."""

import uuid
import random
from datetime import datetime, date, time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.departamento import TipoDepartamento

client = TestClient(app)

@pytest.fixture
def auth_headers():
    login_res = client.post("/api/v1/auth/login", json={
        "documento_identidad": "V-00000000",
        "password": "admin1234"
    })
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# ================= 1. RUTAS PÚBLICAS Y DOCUMENTACIÓN =================

def test_public_and_docs_endpoints():
    # Health check
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "online"

    # Redirección raíz al prototipo estático
    res_root = client.get("/", follow_redirects=False)
    assert res_root.status_code in (302, 307)
    assert res_root.headers["location"] == "/static/index.html"

    # Swagger, ReDoc y OpenAPI schema
    res_docs = client.get("/docs")
    assert res_docs.status_code == 200

    res_redoc = client.get("/redoc")
    assert res_redoc.status_code == 200

    res_openapi = client.get("/openapi.json")
    assert res_openapi.status_code == 200
    assert "paths" in res_openapi.json()

# ================= 2. AUTENTICACIÓN =================

def test_auth_cycle_endpoints(auth_headers):
    # Credenciales incorrectas
    res_bad = client.post("/api/v1/auth/login", json={
        "documento_identidad": "V-00000000",
        "password": "clave_erronea_123"
    })
    assert res_bad.status_code == 401

    # Perfil /me autenticado
    res_me = client.get("/api/v1/auth/me", headers=auth_headers)
    assert res_me.status_code == 200
    assert res_me.json()["documento_identidad"] == "v-00000000"

    # Logout
    res_logout = client.post("/api/v1/auth/logout", headers=auth_headers)
    assert res_logout.status_code == 200
    assert "message" in res_logout.json()

# ================= 3. DEPARTAMENTOS (CRUD COMPLETO) =================

def test_departamentos_full_routes(auth_headers):
    # Listar
    res_list = client.get("/api/v1/departamentos", headers=auth_headers)
    assert res_list.status_code == 200
    assert "items" in res_list.json()

    # Crear
    uid = uuid.uuid4().hex[:6]
    name = f"Unidad Test {uid}"
    res_create = client.post("/api/v1/departamentos", json={
        "nombre": name,
        "tipo": "coordinación"
    }, headers=auth_headers)
    assert res_create.status_code == 201
    dept_id = res_create.json()["id"]

    # Detalle por ID
    res_get = client.get(f"/api/v1/departamentos/{dept_id}", headers=auth_headers)
    assert res_get.status_code == 200
    assert res_get.json()["nombre"] == name

    # Actualizar por ID
    res_update = client.put(f"/api/v1/departamentos/{dept_id}", json={
        "nombre": f"Unidad Actualizada {uid}",
        "tipo": "sección"
    }, headers=auth_headers)
    assert res_update.status_code == 200
    assert res_update.json()["tipo"] == "sección"

    # Eliminar
    res_del = client.delete(f"/api/v1/departamentos/{dept_id}", headers=auth_headers)
    assert res_del.status_code == 200

    # 404 en eliminado
    res_not_found = client.get(f"/api/v1/departamentos/{dept_id}", headers=auth_headers)
    assert res_not_found.status_code == 404

# ================= 4. HORARIOS (CRUD COMPLETO) =================

def test_horarios_full_routes(auth_headers):
    # Listar
    res_list = client.get("/api/v1/horarios", headers=auth_headers)
    assert res_list.status_code == 200
    assert "items" in res_list.json()

    # Crear Fijo
    uid = uuid.uuid4().hex[:6]
    res_create = client.post("/api/v1/horarios", json={
        "nombre": f"Horario Fijo E2E {uid}",
        "tipo": "fijo",
        "detalles": [
            {"dia_semana": 1, "hora_entrada": "08:00:00", "hora_salida": "12:00:00"}
        ]
    }, headers=auth_headers)
    assert res_create.status_code == 201
    h_id = res_create.json()["id"]

    # Detalle por ID
    res_get = client.get(f"/api/v1/horarios/{h_id}", headers=auth_headers)
    assert res_get.status_code == 200
    assert res_get.json()["id"] == h_id

    # Actualizar
    res_put = client.put(f"/api/v1/horarios/{h_id}", json={
        "nombre": f"Horario Modificado E2E {uid}"
    }, headers=auth_headers)
    assert res_put.status_code == 200
    assert "Modificado" in res_put.json()["nombre"]

    # Eliminar
    res_del = client.delete(f"/api/v1/horarios/{h_id}", headers=auth_headers)
    assert res_del.status_code == 200

# ================= 5. REDES AUTORIZADAS (CRUD COMPLETO) =================

def test_redes_full_routes(auth_headers):
    # Listar
    res_list = client.get("/api/v1/redes", headers=auth_headers)
    assert res_list.status_code == 200
    assert "items" in res_list.json()

    # Crear
    rand_octet = random.randint(110, 190)
    res_create = client.post("/api/v1/redes", json={
        "direccion_ip": f"192.168.{rand_octet}.0/24",
        "descripcion": f"Red Subred {rand_octet}",
        "activo": True
    }, headers=auth_headers)
    assert res_create.status_code == 201
    red_id = res_create.json()["id"]

    # Detalle
    res_get = client.get(f"/api/v1/redes/{red_id}", headers=auth_headers)
    assert res_get.status_code == 200

    # Actualizar
    res_put = client.put(f"/api/v1/redes/{red_id}", json={
        "descripcion": "Descripción Actualizada E2E"
    }, headers=auth_headers)
    assert res_put.status_code == 200
    assert res_put.json()["descripcion"] == "Descripción Actualizada E2E"

    # Toggle status
    res_toggle = client.patch(f"/api/v1/redes/{red_id}/toggle-status", headers=auth_headers)
    assert res_toggle.status_code == 200
    assert res_toggle.json()["activo"] is False

    # Eliminar
    res_del = client.delete(f"/api/v1/redes/{red_id}", headers=auth_headers)
    assert res_del.status_code == 200

# ================= 6. USUARIOS Y CREDENCIALES (RUTAS COMPLETAS) =================

def test_usuarios_and_credentials_full_routes(auth_headers):
    # Listar Roles disponibles
    res_roles = client.get("/api/v1/usuarios/roles/all", headers=auth_headers)
    assert res_roles.status_code == 200
    roles_list = res_roles.json()
    assert len(roles_list) >= 3
    assert any(r["nombre"] == "Administrador" for r in roles_list)

    # Check Documento
    res_check_admin = client.get("/api/v1/usuarios/check-documento?documento=V-00000000", headers=auth_headers)
    assert res_check_admin.status_code == 200
    assert res_check_admin.json()["disponible"] is False

    doc_nuevo = f"v-{random.randint(40000000, 49000000)}"
    res_check_new = client.get(f"/api/v1/usuarios/check-documento?documento={doc_nuevo}", headers=auth_headers)
    assert res_check_new.status_code == 200
    assert res_check_new.json()["disponible"] is True

    # Obtener departamento base
    dept_id = client.get("/api/v1/departamentos", headers=auth_headers).json()["items"][0]["id"]

    # Crear Usuario
    res_create = client.post("/api/v1/usuarios", json={
        "documento_identidad": doc_nuevo,
        "nombre": "Beatriz",
        "apellido": "Paredes",
        "rol_id": 3,
        "departamento_id": dept_id,
        "activo": True
    }, headers=auth_headers)
    assert res_create.status_code == 201
    user_data = res_create.json()
    user_id = user_data["id"]
    qr_init = user_data["codigo_qr"]

    # Detalle Usuario
    res_get = client.get(f"/api/v1/usuarios/{user_id}", headers=auth_headers)
    assert res_get.status_code == 200
    assert res_get.json()["documento_identidad"] == doc_nuevo
    assert res_get.json()["activo"] is True

    # Toggle status (Inhabilitar / Reactivar)
    res_toggle_off = client.patch(f"/api/v1/usuarios/{user_id}/toggle-status", headers=auth_headers)
    assert res_toggle_off.status_code == 200
    assert res_toggle_off.json()["activo"] is False

    res_toggle_on = client.patch(f"/api/v1/usuarios/{user_id}/toggle-status", headers=auth_headers)
    assert res_toggle_on.status_code == 200
    assert res_toggle_on.json()["activo"] is True

    # Actualizar Usuario
    res_update = client.put(f"/api/v1/usuarios/{user_id}", json={
        "nombre": "Beatriz Elena"
    }, headers=auth_headers)
    assert res_update.status_code == 200
    assert res_update.json()["nombre"] == "Beatriz Elena"

    # Enrolar Biometría
    fake_vector = [0.25] * 128
    res_bio = client.post(f"/api/v1/usuarios/{user_id}/biometria", json={
        "vector": fake_vector
    }, headers=auth_headers)
    assert res_bio.status_code == 200
    assert res_bio.json()["tiene_biometria"] is True

    # Regenerar QR
    res_regen = client.post(f"/api/v1/usuarios/{user_id}/regenerar-qr", headers=auth_headers)
    assert res_regen.status_code == 200
    assert res_regen.json()["codigo_qr"] != qr_init

    # Descargar QR PNG
    res_qr_png = client.get(f"/api/v1/usuarios/{user_id}/credencial-qr", headers=auth_headers)
    assert res_qr_png.status_code == 200
    assert res_qr_png.headers["content-type"] == "image/png"
    assert res_qr_png.content.startswith(b"\x89PNG")

    # Descargar Carnet PDF
    res_pdf = client.get(f"/api/v1/usuarios/{user_id}/credencial-pdf", headers=auth_headers)
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert res_pdf.content.startswith(b"%PDF")

    # Borrado físico (sin asistencias aún)
    res_del = client.delete(f"/api/v1/usuarios/{user_id}", headers=auth_headers)
    assert res_del.status_code == 200
    assert res_del.json()["tipo_borrado"] == "fisico"

# ================= 7. SEGURIDAD: CONTROL DE ACCESO SIN TOKEN =================

@pytest.mark.parametrize("method,path", [
    ("GET", "/api/v1/auth/me"),
    ("GET", "/api/v1/usuarios"),
    ("POST", "/api/v1/usuarios"),
    ("GET", "/api/v1/departamentos"),
    ("GET", "/api/v1/horarios"),
    ("GET", "/api/v1/redes"),
    ("GET", "/api/v1/asistencias/historial"),
    ("GET", "/api/v1/auditoria/incompletas"),
    ("GET", "/api/v1/reportes/resumen"),
])
def test_unauthenticated_requests_are_blocked(method, path):
    if method == "GET":
        res = client.get(path)
    else:
        res = client.post(path, json={})
    assert res.status_code == 401
    assert "No se proporcionó el token" in res.json()["detail"]
