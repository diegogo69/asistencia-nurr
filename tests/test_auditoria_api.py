import uuid
from datetime import datetime, date, time, timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.asistencia import Asistencia, EstadoCumplimiento, MetodoValidacion
from app.models.usuario import Usuario

client = TestClient(app)

@pytest.fixture
def auth_headers():
    login_res = client.post("/api/v1/auth/login", json={
        "documento_identidad": "V-00000000",
        "password": "admin1234"
    })
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_auditoria_incomplete_detection_and_resolution(auth_headers):
    db = SessionLocal()
    try:
        # 1. Crear un registro de asistencia en el pasado sin hora de salida
        user = db.query(Usuario).filter(Usuario.documento_identidad == "V-00000000").first()
        ayer = date.today() - timedelta(days=1)

        asistencia_pasada = Asistencia(
            usuario_id=user.id,
            fecha=ayer,
            hora_entrada=time(8, 0, 0),
            hora_salida=None,
            estado_cumplimiento=EstadoCumplimiento.PENDIENTE,
            ip_registro_entrada="127.0.0.1",
            metodo_validacion=MetodoValidacion.QR
        )
        db.add(asistencia_pasada)
        db.commit()
        db.refresh(asistencia_pasada)
        asistencia_id = asistencia_pasada.id
    finally:
        db.close()

    # 2. Ejecutar detección automática
    detec_res = client.post("/api/v1/auditoria/ejecutar-deteccion", headers=auth_headers)
    assert detec_res.status_code == 200
    assert detec_res.json()["registros_marcados_incompletos"] >= 1

    # 3. Consultar lista de incompletas
    incompletas_res = client.get("/api/v1/auditoria/incompletas", headers=auth_headers)
    assert incompletas_res.status_code == 200
    ids_incompletas = [item["id"] for item in incompletas_res.json()["items"]]
    assert asistencia_id in ids_incompletas

    # 4. Intentar resolver con justificación insuficiente (< 10 caracteres)
    fail_res = client.post("/api/v1/auditoria/resolver", json={
        "asistencia_id": asistencia_id,
        "hora_salida": "13:00:00",
        "nuevo_estado": "puntual",
        "observacion": "olvido"
    }, headers=auth_headers)
    assert fail_res.status_code == 422 or fail_res.status_code == 400

    # 5. Resolver exitosamente con observación justificada
    resolve_res = client.post("/api/v1/auditoria/resolver", json={
        "asistencia_id": asistencia_id,
        "hora_salida": "13:00:00",
        "nuevo_estado": "puntual",
        "observacion": "Pasante olvidó marcar salida en el kiosco pero se constató presencialidad completa en el laboratorio."
    }, headers=auth_headers)
    assert resolve_res.status_code == 200
    assert "Inconsistencia resuelta" in resolve_res.json()["message"]

    # 6. Consultar bitácora inmutable de resoluciones
    resols_res = client.get("/api/v1/auditoria/resoluciones", headers=auth_headers)
    assert resols_res.status_code == 200
    assert resols_res.json()["total"] >= 1
    ultima_resol = resols_res.json()["items"][0]
    assert ultima_resol["asistencia_id"] == asistencia_id
    assert "Pasante olvidó marcar" in ultima_resol["observacion"]
