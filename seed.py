"""Script de inicialización y sembrado de datos maestros obligatorios para Asistencia-NURR."""

from datetime import time
import uuid
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models import (
    Departamento, TipoDepartamento,
    Rol,
    HorarioPlantilla, HorarioDetalle, TipoHorario,
    RedAutorizada,
    Usuario
)

def seed_database():
    db = SessionLocal()
    try:
        print("[*] Iniciando sembrado de datos maestros...")

        # 1. Departamentos
        depto_soporte = db.query(Departamento).filter_by(nombre="Unidad de Soporte Técnico").first()
        if not depto_soporte:
            depto_soporte = Departamento(
                nombre="Unidad de Soporte Técnico",
                tipo=TipoDepartamento.COORDINACION
            )
            db.add(depto_soporte)
            db.flush()
            print("  [+] Departamento creado: Unidad de Soporte Técnico")
        else:
            print("  [i] Departamento ya existente: Unidad de Soporte Técnico")

        # 2. Roles
        roles_data = [
            ("Administrador", True),
            ("Coordinador", True),
            ("Técnico Contratado", False),
            ("Programador Contratado", False),
            ("Pasante Técnico", False),
            ("Pasante Programador", False),
        ]
        roles_dict = {}
        for nombre_rol, req_pass in roles_data:
            rol = db.query(Rol).filter_by(nombre=nombre_rol).first()
            if not rol:
                rol = Rol(nombre=nombre_rol, requiere_password=req_pass)
                db.add(rol)
                db.flush()
                print(f"  [+] Rol creado: {nombre_rol} (requiere_password={req_pass})")
            roles_dict[nombre_rol] = rol

        # 3. Horarios Plantillas
        # 3.1 Horario Fijo Institucional (Lunes a Miércoles de 8:00 AM a 1:00 PM)
        horario_fijo = db.query(HorarioPlantilla).filter_by(nombre="Horario Fijo Institucional (L-M 8:00 AM - 1:00 PM)").first()
        if not horario_fijo:
            horario_fijo = HorarioPlantilla(
                nombre="Horario Fijo Institucional (L-M 8:00 AM - 1:00 PM)",
                tipo=TipoHorario.FIJO,
                horas_requeridas=15
            )
            db.add(horario_fijo)
            db.flush()

            # Bloques Lunes, Martes, Miércoles
            for dia in [1, 2, 3]:  # 1=Lunes, 2=Martes, 3=Miércoles
                detalle = HorarioDetalle(
                    horario_plantilla_id=horario_fijo.id,
                    dia_semana=dia,
                    hora_entrada=time(8, 0, 0),
                    hora_salida=time(13, 0, 0)
                )
                db.add(detalle)
            print("  [+] Plantilla horaria fija creada con bloques L-M 8:00-13:00")

        # 3.2 Horario Flexible Pasantes (Meta semanal de 4 horas)
        horario_pasante = db.query(HorarioPlantilla).filter_by(nombre="Horario Flexible Pasantes (4h Semanales)").first()
        if not horario_pasante:
            horario_pasante = HorarioPlantilla(
                nombre="Horario Flexible Pasantes (4h Semanales)",
                tipo=TipoHorario.FLEXIBLE,
                horas_requeridas=4
            )
            db.add(horario_pasante)
            db.flush()
            print("  [+] Plantilla horaria flexible creada para pasantes (4h)")

        # 4. Redes Autorizadas
        redes_iniciales = [
            ("127.0.0.1", "Servidor Localhost (Punto de Marcación Principal)", True),
            ("192.168.0.0/16", "Subred LAN Unidad de Soporte Técnico", True),
            ("10.0.0.0/8", "Subred Campus Universitario ULA-NURR", True),
        ]
        for ip_red, desc, activo in redes_iniciales:
            red = db.query(RedAutorizada).filter_by(direccion_ip=ip_red).first()
            if not red:
                red = RedAutorizada(direccion_ip=ip_red, descripcion=desc, activo=activo)
                db.add(red)
                print(f"  [+] Red autorizada registrada: {ip_red}")

        # 5. Usuario Coordinador / Administrador Raíz
        admin_doc = "v-00000000"
        admin_user = db.query(Usuario).filter(Usuario.documento_identidad.in_(["v-00000000", "V-00000000"])).first()
        if not admin_user:
            admin_user = Usuario(
                documento_identidad=admin_doc,
                nombre="Coordinador",
                apellido="Soporte Técnico",
                rol_id=roles_dict["Coordinador"].id,
                departamento_id=depto_soporte.id,
                horario_id=horario_fijo.id,
                password_hash=get_password_hash("admin1234"),
                codigo_qr=f"QR-ADMIN-{uuid.uuid4().hex[:12].upper()}",
                activo=True
            )
            db.add(admin_user)
            print(f"  [+] Usuario Coordinador/Admin raíz creado: {admin_doc} (Clave: admin1234)")
        else:
            print(f"  [i] Usuario admin ya existente: {admin_doc}")

        db.commit()
        print("[+] Sembrado completado con éxito.")
    except Exception as e:
        db.rollback()
        print(f"[!] Error durante el sembrado: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
