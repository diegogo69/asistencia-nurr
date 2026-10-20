import pytest
from app.core.database import SessionLocal
from app.core.security import verify_password
from app.models import Usuario, Rol, Departamento, HorarioPlantilla, RedAutorizada

def test_database_connection_and_seed_data():
    db = SessionLocal()
    try:
        # 1. Verificar departamento
        depto = db.query(Departamento).filter_by(nombre="Unidad de Soporte Técnico").first()
        assert depto is not None
        assert depto.tipo.value == "coordinación"

        # 2. Verificar roles
        roles = db.query(Rol).all()
        assert len(roles) >= 6
        nombres_roles = [r.nombre for r in roles]
        assert "Coordinador" in nombres_roles
        assert "Pasante Técnico" in nombres_roles

        # 3. Verificar horario fijo con bloques
        horario = db.query(HorarioPlantilla).filter_by(tipo="fijo").first()
        assert horario is not None
        assert len(horario.detalles) == 3

        # 4. Verificar redes autorizadas
        redes = db.query(RedAutorizada).all()
        assert len(redes) >= 2

        # 5. Verificar usuario administrador raíz y hash de contraseña
        admin = db.query(Usuario).filter_by(documento_identidad="v-00000000").first()
        assert admin is not None
        assert admin.activo is True
        assert verify_password("admin1234", admin.password_hash) is True
        assert verify_password("clave_erronea", admin.password_hash) is False
    finally:
        db.close()
