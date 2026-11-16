"""Pruebas exhaustivas para:
1. Requerimiento obligatorio de correo electrónico al registrar nuevos usuarios.
2. Cambio de contraseña (restringido a roles Administrador/Coordinador).
3. Primer inicio de sesión del usuario administrador preconfigurado (v-00000000 / admin1234).
4. Recuperación de contraseña olvidada mediante mensaje al correo electrónico.
"""

import uuid
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.departamento import Departamento
from app.services.email_service import get_sent_emails, clear_sent_emails

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_emails_and_db():
    clear_sent_emails()
    yield
    clear_sent_emails()

@pytest.fixture
def base_dept_and_roles():
    db = SessionLocal()
    try:
        dept = db.query(Departamento).first()
        rol_coord = db.query(Rol).filter_by(nombre="Coordinador").first()
        rol_admin = db.query(Rol).filter_by(nombre="Administrador").first()
        rol_tecnico = db.query(Rol).filter_by(nombre="Técnico Contratado").first()
        return {
            "dept_id": dept.id,
            "rol_coord_id": rol_coord.id,
            "rol_admin_id": rol_admin.id,
            "rol_tecnico_id": rol_tecnico.id
        }
    finally:
        db.close()

@pytest.fixture
def admin_headers():
    # Asegurar contraseña conocida para el administrador preconfigurado
    db = SessionLocal()
    admin_u = db.query(Usuario).filter(Usuario.documento_identidad == "v-00000000").first()
    if admin_u:
        from app.core.security import get_password_hash
        admin_u.password_hash = get_password_hash("admin1234")
        admin_u.debe_cambiar_password = False
        db.commit()
    db.close()

    res = client.post("/api/v1/auth/login", json={
        "documento_identidad": "v-00000000",
        "password": "admin1234"
    })
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# ==================== 1. EMAIL OBLIGATORIO AL REGISTRAR NUEVO USUARIO ====================

def test_create_usuario_without_email_fails(admin_headers, base_dept_and_roles):
    doc = f"v-{uuid.uuid4().int % 90000000 + 10000000}"
    # Intento de registrar usuario omitiendo el campo email
    res = client.post("/api/v1/usuarios", json={
        "documento_identidad": doc,
        "nombre": "Ana",
        "apellido": "Gómez",
        "rol_id": base_dept_and_roles["rol_tecnico_id"],
        "departamento_id": base_dept_and_roles["dept_id"],
        "activo": True
    }, headers=admin_headers)
    assert res.status_code == 422
    errors = res.json()["detail"]
    assert any("email" in err["loc"] for err in errors)

def test_create_usuario_with_invalid_email_fails(admin_headers, base_dept_and_roles):
    doc = f"v-{uuid.uuid4().int % 90000000 + 10000000}"
    res = client.post("/api/v1/usuarios", json={
        "documento_identidad": doc,
        "email": "correo_sin_arroba_ni_dominio",
        "nombre": "Ana",
        "apellido": "Gómez",
        "rol_id": base_dept_and_roles["rol_tecnico_id"],
        "departamento_id": base_dept_and_roles["dept_id"],
        "activo": True
    }, headers=admin_headers)
    assert res.status_code == 422
    detail_str = str(res.json()["detail"])
    assert "email" in detail_str.lower() or "correo" in detail_str.lower()

def test_create_usuario_with_duplicate_email_fails(admin_headers, base_dept_and_roles):
    doc1 = f"v-{uuid.uuid4().int % 90000000 + 10000000}"
    email_shared = f"compartido_{uuid.uuid4().hex[:6]}@ula.ve"

    # 1. Crear primer usuario
    res1 = client.post("/api/v1/usuarios", json={
        "documento_identidad": doc1,
        "email": email_shared,
        "nombre": "Primero",
        "apellido": "Usuario",
        "rol_id": base_dept_and_roles["rol_tecnico_id"],
        "departamento_id": base_dept_and_roles["dept_id"],
        "activo": True
    }, headers=admin_headers)
    assert res1.status_code == 201
    user1_id = res1.json()["id"]

    # 2. Intentar registrar segundo usuario con el mismo correo
    doc2 = f"v-{uuid.uuid4().int % 90000000 + 10000000}"
    res2 = client.post("/api/v1/usuarios", json={
        "documento_identidad": doc2,
        "email": email_shared.upper(),  # Caso insensible
        "nombre": "Segundo",
        "apellido": "Usuario",
        "rol_id": base_dept_and_roles["rol_tecnico_id"],
        "departamento_id": base_dept_and_roles["dept_id"],
        "activo": True
    }, headers=admin_headers)
    assert res2.status_code == 400
    assert "ya se encuentra registrado" in res2.json()["detail"]

    # Limpieza
    client.delete(f"/api/v1/usuarios/{user1_id}", headers=admin_headers)

# ==================== 2. CONTROL DE CONTRASEÑA SEGÚN ROL ====================

def test_tecnico_contratado_cannot_have_password(admin_headers, base_dept_and_roles):
    doc = f"v-{uuid.uuid4().int % 90000000 + 10000000}"
    email = f"tecnico_{uuid.uuid4().hex[:6]}@ula.ve"

    # Intentar crear un usuario técnico con contraseña debe fallar
    res = client.post("/api/v1/usuarios", json={
        "documento_identidad": doc,
        "email": email,
        "nombre": "Marcos",
        "apellido": "Rivas",
        "rol_id": base_dept_and_roles["rol_tecnico_id"],
        "departamento_id": base_dept_and_roles["dept_id"],
        "password": "clave_invalida_para_tecnico",
        "activo": True
    }, headers=admin_headers)
    assert res.status_code == 400
    assert "no utiliza contraseña" in res.json()["detail"]

def test_admin_cambiar_password_endpoint(admin_headers, base_dept_and_roles):
    # 1. Crear nuevo Coordinador con contraseña
    doc_coord = f"v-{uuid.uuid4().int % 90000000 + 10000000}"
    email_coord = f"coord_{uuid.uuid4().hex[:6]}@ula.ve"
    res_coord = client.post("/api/v1/usuarios", json={
        "documento_identidad": doc_coord,
        "email": email_coord,
        "nombre": "Elena",
        "apellido": "Ponce",
        "rol_id": base_dept_and_roles["rol_coord_id"],
        "departamento_id": base_dept_and_roles["dept_id"],
        "password": "coordClaveInicial1",
        "activo": True
    }, headers=admin_headers)
    assert res_coord.status_code == 201
    coord_id = res_coord.json()["id"]

    # 2. Cambiar contraseña desde el endpoint de gestión de usuarios
    res_change = client.post(f"/api/v1/usuarios/{coord_id}/cambiar-password", json={
        "nuevo_password": "nuevaClaveSuperSegura99"
    }, headers=admin_headers)
    assert res_change.status_code == 200
    assert "actualizada exitosamente" in res_change.json()["message"]

    # 3. Probar login con nueva contraseña del coordinador
    res_login = client.post("/api/v1/auth/login", json={
        "documento_identidad": doc_coord,
        "password": "nuevaClaveSuperSegura99"
    })
    assert res_login.status_code == 200
    coord_token = res_login.json()["access_token"]
    coord_headers = {"Authorization": f"Bearer {coord_token}"}

    # 4. Coordinador cambia su propia contraseña con /auth/cambiar-password
    # Contraseña actual incorrecta
    res_bad_pw = client.post("/api/v1/auth/cambiar-password", json={
        "password_actual": "clave_falsa",
        "nuevo_password": "clave_final_1234"
    }, headers=coord_headers)
    assert res_bad_pw.status_code == 400
    assert "actual suministrada es incorrecta" in res_bad_pw.json()["detail"]

    # Cambio exitoso
    res_good_pw = client.post("/api/v1/auth/cambiar-password", json={
        "password_actual": "nuevaClaveSuperSegura99",
        "nuevo_password": "clave_final_1234",
        "confirmar_password": "clave_final_1234"
    }, headers=coord_headers)
    assert res_good_pw.status_code == 200

    # Limpieza
    client.delete(f"/api/v1/usuarios/{coord_id}", headers=admin_headers)

# ==================== 3. PRIMER INICIO DE SESIÓN ADMIN PRECONFIGURADO ====================

def test_admin_preconfigurado_primer_inicio_flow():
    # 1. Asegurar estado inicial de v-00000000 en la BD
    db = SessionLocal()
    admin_u = db.query(Usuario).filter(Usuario.documento_identidad == "v-00000000").first()
    from app.core.security import get_password_hash
    admin_u.password_hash = get_password_hash("admin1234")
    admin_u.debe_cambiar_password = True
    admin_u.email = None
    db.commit()
    db.close()

    # 2. Login inicial con credenciales preconfiguradas
    login_res = client.post("/api/v1/auth/login", json={
        "documento_identidad": "v-00000000",
        "password": "admin1234"
    })
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["debe_cambiar_password"] is True
    assert login_data["user"]["debe_cambiar_password"] is True
    initial_token = login_data["access_token"]
    headers = {"Authorization": f"Bearer {initial_token}"}

    # 3. Intento de primer ingreso reutilizando 'admin1234' debe ser rechazado
    res_same_pw = client.post("/api/v1/auth/primer-ingreso", json={
        "email": "soporte@ula.ve",
        "nuevo_password": "admin1234"
    }, headers=headers)
    assert res_same_pw.status_code == 400
    assert "diferente a la contraseña inicial" in res_same_pw.json()["detail"]

    # 4. Primer ingreso exitoso con email y nueva contraseña
    nuevo_correo = "admin_soporte@ula.ve"
    res_primer_ok = client.post("/api/v1/auth/primer-ingreso", json={
        "email": nuevo_correo,
        "nuevo_password": "AdminPasswordSeguro2026!",
        "confirmar_password": "AdminPasswordSeguro2026!"
    }, headers=headers)
    assert res_primer_ok.status_code == 200
    res_data = res_primer_ok.json()
    assert res_data["debe_cambiar_password"] is False
    assert res_data["user"]["email"] == nuevo_correo
    assert res_data["user"]["debe_cambiar_password"] is False

    # 5. La contraseña antigua ya no debe funcionar
    old_login = client.post("/api/v1/auth/login", json={
        "documento_identidad": "v-00000000",
        "password": "admin1234"
    })
    assert old_login.status_code == 401

    # 6. La nueva contraseña funciona y debe_cambiar_password es False
    new_login = client.post("/api/v1/auth/login", json={
        "documento_identidad": "v-00000000",
        "password": "AdminPasswordSeguro2026!"
    })
    assert new_login.status_code == 200
    assert new_login.json()["debe_cambiar_password"] is False
    assert new_login.json()["user"]["email"] == nuevo_correo

# ==================== 4. RECUPERACIÓN DE CONTRASEÑA POR EMAIL ====================

def test_password_recovery_full_flow():
    db = SessionLocal()
    admin_u = db.query(Usuario).filter(Usuario.documento_identidad == "v-00000000").first()
    admin_u.email = "admin_recuperacion@ula.ve"
    db.commit()
    db.close()

    # 1. Solicitar recuperación por documento
    req_res = client.post("/api/v1/auth/recuperar-password/solicitar", json={
        "identificador": "v-00000000"
    })
    assert req_res.status_code == 200
    data = req_res.json()
    assert "correo electrónico" in data["message"]
    assert "email_enmascarado" in data
    assert "@ula.ve" in data["email_enmascarado"]
    
    # SEGURIDAD CRÍTICA: El token de recuperación NUNCA debe viajar en la respuesta HTTP
    assert "reset_token" not in data

    # Verificar que el servicio despachó el correo y contiene el código de 6 dígitos
    emails = get_sent_emails()
    assert len(emails) >= 1
    assert emails[-1]["to"] == "admin_recuperacion@ula.ve"
    token = emails[-1].get("reset_token")
    assert token is not None
    assert len(token) == 6
    assert token in emails[-1]["text"]

    # 2. Verificar validez del código (probando también con espacios en blanco que el usuario pueda ingresar)
    verif_res = client.post("/api/v1/auth/recuperar-password/verificar", json={
        "token": f" {token} "
    })
    assert verif_res.status_code == 200
    assert verif_res.json()["valido"] is True

    # 3. Restablecer la contraseña con el token
    reset_res = client.post("/api/v1/auth/recuperar-password/restablecer", json={
        "token": token,
        "nuevo_password": "ClaveRecuperadaExitosa2026!",
        "confirmar_password": "ClaveRecuperadaExitosa2026!"
    })
    assert reset_res.status_code == 200
    assert "exitosamente" in reset_res.json()["message"]

    # 4. El token no puede ser reusado (uso único)
    reuse_res = client.post("/api/v1/auth/recuperar-password/verificar", json={
        "token": token
    })
    assert reuse_res.status_code == 400

    # 5. Iniciar sesión con la contraseña restablecida
    login_res = client.post("/api/v1/auth/login", json={
        "documento_identidad": "v-00000000",
        "password": "ClaveRecuperadaExitosa2026!"
    })
    assert login_res.status_code == 200
    assert login_res.json()["user"]["documento_identidad"] == "v-00000000"

    # Restaurar credenciales estándar para otras pruebas
    db = SessionLocal()
    admin_u = db.query(Usuario).filter(Usuario.documento_identidad == "v-00000000").first()
    from app.core.security import get_password_hash
    admin_u.password_hash = get_password_hash("admin1234")
    admin_u.debe_cambiar_password = False
    admin_u.email = "admin@ula.ve"
    db.commit()
    db.close()
