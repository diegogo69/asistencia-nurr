"""Batería de pruebas unitarias y de integración para la validación y formateo
del documento de identidad venezolano (Cédula de Identidad).
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.documento import (
    format_documento_identidad,
    parse_documento_identidad,
    is_valid_documento_identidad
)

client = TestClient(app)

@pytest.fixture
def auth_headers():
    login_res = client.post("/api/v1/auth/login", json={
        "documento_identidad": "v-00000000",
        "password": "admin1234"
    })
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# ================= 1. PRUEBAS DE UTILIDAD Y NORMALIZACIÓN PURA =================

@pytest.mark.parametrize("raw_input, expected", [
    # Formatos de administración / inicialización (00000000)
    ("00000000", "v-00000000"),
    ("v00000000", "v-00000000"),
    ("V00000000", "v-00000000"),
    ("v-00000000", "v-00000000"),
    ("V-00000000", "v-00000000"),
    ("00.000.000", "v-00000000"),
    ("v00.000.000", "v-00000000"),
    ("V00.000.000", "v-00000000"),
    ("v-00.000.000", "v-00000000"),
    ("V-00.000.000", "v-00000000"),

    # Formatos para ciudadanos venezolanos (V)
    ("12345678", "v-12345678"),
    ("v12345678", "v-12345678"),
    ("V12345678", "v-12345678"),
    ("v-12345678", "v-12345678"),
    ("V-12345678", "v-12345678"),
    ("12.345.678", "v-12345678"),
    ("v12.345.678", "v-12345678"),
    ("V12.345.678", "v-12345678"),
    ("v-12.345.678", "v-12345678"),
    ("V-12.345.678", "v-12345678"),

    # Límites de rango permitidos (1.000.000 al 99.999.999)
    ("1000000", "v-1000000"),
    ("1.000.000", "v-1000000"),
    ("V-1.000.000", "v-1000000"),
    ("99999999", "v-99999999"),
    ("99.999.999", "v-99999999"),
    ("V-99.999.999", "v-99999999"),

    # Formatos para extranjeros (E)
    ("e82345678", "e-82345678"),
    ("E82345678", "e-82345678"),
    ("e-82345678", "e-82345678"),
    ("E-82345678", "e-82345678"),
    ("E-82.345.678", "e-82345678"),
    ("e82.345.678", "e-82345678"),
])
def test_format_documento_valid_cases(raw_input, expected):
    result = format_documento_identidad(raw_input)
    assert result == expected
    assert is_valid_documento_identidad(raw_input) is True

@pytest.mark.parametrize("invalid_input", [
    "",
    "   ",
    "abc",
    "V-ABC",
    "J-12345678",       # RIF jurídico no permitido como documento personal
    "G-12345678",
    "999999",           # Menor a 1.000.000
    "V-999999",
    "100000000",        # Mayor a 99.999.999
    "V-100000000",
    "12.345.678.900",
    None,
])
def test_format_documento_invalid_cases(invalid_input):
    with pytest.raises(ValueError):
        format_documento_identidad(invalid_input)
    assert is_valid_documento_identidad(invalid_input) is False


# ================= 2. PRUEBAS DE INTEGRACIÓN EN ENDPOINTS API =================

def test_login_with_all_format_variants():
    """El administrador raíz puede iniciar sesión con cualquiera de los formatos equivalentes a v-00000000."""
    variants = [
        "00000000",
        "v00000000",
        "V00000000",
        "v-00000000",
        "V-00000000",
        "00.000.000",
        "v00.000.000",
        "V-00.000.000",
    ]
    for doc in variants:
        res = client.post("/api/v1/auth/login", json={
            "documento_identidad": doc,
            "password": "admin1234"
        })
        assert res.status_code == 200, f"Fallo al autenticar con variante: {doc}"
        assert res.json()["user"]["documento_identidad"] == "v-00000000"

def test_check_documento_format_and_uniqueness(auth_headers):
    # Ya registrado (admin) usando formato con puntos
    res_admin = client.get("/api/v1/usuarios/check-documento?documento=V-00.000.000", headers=auth_headers)
    assert res_admin.status_code == 200
    assert res_admin.json()["disponible"] is False
    assert res_admin.json()["documento_identidad"] == "v-00000000"

    # Fuera de rango (< 1.000.000)
    res_out_of_range = client.get("/api/v1/usuarios/check-documento?documento=500000", headers=auth_headers)
    assert res_out_of_range.status_code == 200
    assert res_out_of_range.json()["disponible"] is False
    assert "rango" in res_out_of_range.json()["mensaje"].lower()

    # Documento válido y libre
    res_free = client.get("/api/v1/usuarios/check-documento?documento=25.888.999", headers=auth_headers)
    assert res_free.status_code == 200
    assert res_free.json()["disponible"] is True
    assert res_free.json()["documento_identidad"] == "v-25888999"

def test_usuario_crud_formats_stored_as_canonical(auth_headers):
    dept_id = client.get("/api/v1/departamentos", headers=auth_headers).json()["items"][0]["id"]

    # 1. Registrar usuario enviando formato con puntos y prefijo mayúscula: E-22.333.444
    res_create = client.post("/api/v1/usuarios", json={
        "documento_identidad": "E-22.333.444",
        "nombre": "Elena",
        "apellido": "Rivas",
        "rol_id": 3,
        "departamento_id": dept_id,
        "activo": True
    }, headers=auth_headers)
    assert res_create.status_code == 201
    user_data = res_create.json()
    user_id = user_data["id"]

    # Debe almacenarse y responder en formato canónico v-00000000 / e-00000000
    assert user_data["documento_identidad"] == "e-22333444"

    # 2. Verificar usuario en kiosco enviando formato solo numérico: 22333444 (sin prefijo)
    # Como es 'e', si se envía sólo número asume por defecto 'v', así que no coincide:
    res_kiosk_wrong = client.post("/api/v1/marcacion/verificar-usuario", json={
        "documento_identidad": "22333444"
    })
    assert res_kiosk_wrong.status_code == 200
    assert res_kiosk_wrong.json()["registrado"] is False

    # Pero enviando con prefijo o con puntos: e22.333.444
    res_kiosk = client.post("/api/v1/marcacion/verificar-usuario", json={
        "documento_identidad": "e22.333.444"
    })
    assert res_kiosk.status_code == 200
    assert res_kiosk.json()["registrado"] is True
    assert res_kiosk.json()["documento_identidad"] == "e-22333444"

    # 3. Limpieza
    del_res = client.delete(f"/api/v1/usuarios/{user_id}", headers=auth_headers)
    assert del_res.status_code == 200
