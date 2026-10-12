import uuid
import random
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.core.network import is_ip_authorized

client = TestClient(app)

@pytest.fixture
def auth_headers():
    login_res = client.post("/api/v1/auth/login", json={
        "documento_identidad": "V-00000000",
        "password": "admin1234"
    })
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# ==================== DEPARTAMENTOS ====================

def test_departamentos_crud(auth_headers):
    # 1. Listar
    res = client.get("/api/v1/departamentos", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["total"] >= 1

    # 2. Crear nueva unidad con nombre único
    dept_name = f"Oficina de Telemática {uuid.uuid4().hex[:6]}"
    create_res = client.post("/api/v1/departamentos", json={
        "nombre": dept_name,
        "tipo": "oficina"
    }, headers=auth_headers)
    assert create_res.status_code == 201
    dept_id = create_res.json()["id"]

    # 3. Validar no duplicidad
    dup_res = client.post("/api/v1/departamentos", json={
        "nombre": dept_name,
        "tipo": "oficina"
    }, headers=auth_headers)
    assert dup_res.status_code == 400

    # 4. Actualizar
    update_res = client.put(f"/api/v1/departamentos/{dept_id}", json={
        "nombre": f"{dept_name} Modificado"
    }, headers=auth_headers)
    assert update_res.status_code == 200
    assert update_res.json()["nombre"] == f"{dept_name} Modificado"

    # 5. Eliminar unidad sin dependencias
    del_res = client.delete(f"/api/v1/departamentos/{dept_id}", headers=auth_headers)
    assert del_res.status_code == 200

def test_delete_departamento_with_users_forbidden(auth_headers):
    # La unidad inicial tiene al usuario admin asignado
    res = client.get("/api/v1/departamentos?q=Soporte", headers=auth_headers)
    soporte_id = res.json()["items"][0]["id"]

    del_res = client.delete(f"/api/v1/departamentos/{soporte_id}", headers=auth_headers)
    assert del_res.status_code == 400
    assert "No se puede eliminar la unidad porque tiene" in del_res.json()["detail"]

# ==================== HORARIOS ====================

def test_horarios_crud(auth_headers):
    # 1. Crear horario fijo válido con nombre único
    fijo_name = f"Horario Turno Tarde {uuid.uuid4().hex[:6]}"
    create_res = client.post("/api/v1/horarios", json={
        "nombre": fijo_name,
        "tipo": "fijo",
        "detalles": [
            {"dia_semana": 1, "hora_entrada": "13:00:00", "hora_salida": "17:00:00"},
            {"dia_semana": 2, "hora_entrada": "13:00:00", "hora_salida": "17:00:00"}
        ]
    }, headers=auth_headers)
    assert create_res.status_code == 201
    horario_id = create_res.json()["id"]

    # 2. Intentar crear bloque con hora_entrada >= hora_salida (debe fallar 422)
    invalid_block_res = client.post("/api/v1/horarios", json={
        "nombre": f"Horario Inválido {uuid.uuid4().hex[:6]}",
        "tipo": "fijo",
        "detalles": [
            {"dia_semana": 1, "hora_entrada": "14:00:00", "hora_salida": "12:00:00"}
        ]
    }, headers=auth_headers)
    assert invalid_block_res.status_code == 422

    # 3. Crear horario flexible válido con nombre único
    nombre_flex = f"Horario Flexible Pasantes {uuid.uuid4().hex[:6]}"
    flex_res = client.post("/api/v1/horarios", json={
        "nombre": nombre_flex,
        "tipo": "flexible",
        "horas_requeridas": 2
    }, headers=auth_headers)
    assert flex_res.status_code == 201
    flex_id = flex_res.json()["id"]

    # 4. Eliminar horarios creados
    del_res = client.delete(f"/api/v1/horarios/{horario_id}", headers=auth_headers)
    assert del_res.status_code == 200
    del_flex = client.delete(f"/api/v1/horarios/{flex_id}", headers=auth_headers)
    assert del_flex.status_code == 200

# ==================== REDES AUTORIZADAS ====================

def test_redes_crud_and_validation(auth_headers):
    # 1. Formato IP inválido debe fallar con 422
    invalid_res = client.post("/api/v1/redes", json={
        "direccion_ip": "300.400.500.600",
        "descripcion": "IP Inválida"
    }, headers=auth_headers)
    assert invalid_res.status_code == 422

    # 2. Crear rango CIDR válido dinámico
    cidr_ip = f"172.{random.randint(20, 29)}.0.0/16"
    create_res = client.post("/api/v1/redes", json={
        "direccion_ip": cidr_ip,
        "descripcion": "Laboratorios de Computación NURR",
        "activo": True
    }, headers=auth_headers)
    assert create_res.status_code == 201
    red_id = create_res.json()["id"]

    # 3. Alternar estado (toggle)
    toggle_res = client.patch(f"/api/v1/redes/{red_id}/toggle-status", headers=auth_headers)
    assert toggle_res.status_code == 200
    assert toggle_res.json()["activo"] is False

    # 4. Limpiar / Eliminar
    del_res = client.delete(f"/api/v1/redes/{red_id}", headers=auth_headers)
    assert del_res.status_code == 200

def test_core_ip_authorization():
    db = SessionLocal()
    try:
        assert is_ip_authorized("127.0.0.1", db) is True
        assert is_ip_authorized("192.168.1.100", db) is True  # coincide con regla 192.168.0.0/16
        assert is_ip_authorized("200.10.20.30", db) is False  # IP externa no autorizada
    finally:
        db.close()
