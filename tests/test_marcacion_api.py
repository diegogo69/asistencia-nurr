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

def test_marcacion_blocked_on_unauthorized_ip():
    # IP externa simulada no autorizada
    headers = {"X-Forwarded-For": "190.200.50.25"}
    res = client.post("/api/v1/marcacion/verificar-usuario", json={
        "documento_identidad": "V-00000000"
    }, headers=headers)
    assert res.status_code == 403
    assert "fuera del rango de red autorizado" in res.json()["detail"]

def test_marcacion_flow_facial_and_qr(auth_headers):
    # 1. Crear un usuario de prueba
    dept_res = client.get("/api/v1/departamentos", headers=auth_headers)
    dept_id = dept_res.json()["items"][0]["id"]
    doc = f"V-{uuid.uuid4().int % 90000000 + 10000000}"

    user_res = client.post("/api/v1/usuarios", json={
        "documento_identidad": doc,
        "nombre": "Carlos",
        "apellido": "Mendoza",
        "rol_id": 4,  # Programador Contratado
        "departamento_id": dept_id,
        "activo": True
    }, headers=auth_headers)
    assert user_res.status_code == 201
    user_data = user_res.json()
    user_id = user_data["id"]
    qr_code = user_data["codigo_qr"]

    # 2. Enrolar vector facial de prueba (128 floats)
    sample_vector = [0.1] * 128
    enroll_res = client.post(f"/api/v1/usuarios/{user_id}/biometria", json={
        "vector": sample_vector
    }, headers=auth_headers)
    assert enroll_res.status_code == 200

    # 3. Kiosco: Verificar usuario
    verif_res = client.post("/api/v1/marcacion/verificar-usuario", json={
        "documento_identidad": doc
    })
    assert verif_res.status_code == 200
    assert verif_res.json()["registrado"] is True
    assert verif_res.json()["tiene_biometria"] is True
    assert verif_res.json()["documento_identidad"] == doc
    assert verif_res.json()["accion_esperada"] == "ENTRADA"

    # 4. Marcación de ENTRADA con Reconocimiento Facial (vector casi idéntico, distancia muy baja)
    live_captured_vector = [0.101] * 128  # Distancia euclidiana insignificante
    entrada_res = client.post("/api/v1/marcacion/registrar", json={
        "documento_identidad": doc,
        "metodo": "facial",
        "vector_facial": live_captured_vector
    })
    assert entrada_res.status_code == 200
    entrada_data = entrada_res.json()
    assert entrada_data["tipo_evento"] == "ENTRADA"
    assert entrada_data["metodo_validacion"] == "facial"
    assert entrada_data["documento_identidad"] == doc

    # 5. Marcación de SALIDA usando Contingencia QR
    salida_res = client.post("/api/v1/marcacion/registrar", json={
        "documento_identidad": doc,
        "metodo": "qr",
        "codigo_qr": qr_code
    })
    assert salida_res.status_code == 200
    salida_data = salida_res.json()
    assert salida_data["tipo_evento"] == "SALIDA"

    # 6. Intento de marcación adicional el mismo día -> COMPLETADO
    extra_res = client.post("/api/v1/marcacion/registrar", json={
        "documento_identidad": doc,
        "metodo": "qr",
        "codigo_qr": qr_code
    })
    assert extra_res.status_code == 200
    assert extra_res.json()["tipo_evento"] == "COMPLETADO"

    # 7. Regla de inmutabilidad: como el usuario ya tiene asistencias, el borrado debe ser LÓGICO
    del_res = client.delete(f"/api/v1/usuarios/{user_id}", headers=auth_headers)
    assert del_res.status_code == 200
    assert del_res.json()["tipo_borrado"] == "logico"

def test_facial_recognition_mismatch():
    # El usuario raíz admin no tiene biometría enrolada todavía
    res = client.post("/api/v1/marcacion/registrar", json={
        "documento_identidad": "V-00000000",
        "metodo": "facial",
        "vector_facial": [0.5] * 128
    })
    assert res.status_code == 400
    assert "no tiene enrolado su vector" in res.json()["detail"]
