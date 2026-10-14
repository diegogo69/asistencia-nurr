"""Script para reiniciar la base de datos de Asistencia-NURR desde cero.

Realiza las siguientes acciones:
1. Elimina la base de datos actual o borra todas sus tablas.
2. Aplica las migraciones de Alembic (alembic upgrade head).
3. Siembra los datos maestros iniciales (seed.py):
   - Departamento: Unidad de Soporte Técnico
   - Roles institucionales
   - Plantillas de horarios (fijo y flexible)
   - Redes autorizadas (localhost y LAN)
   - Usuario Administrador / Coordinador: V-00000000 / admin1234
"""

import os
import sys
from alembic.config import Config
from alembic import command

from app.core.config import settings
from app.core.database import engine, Base
from seed import seed_database

def reset_database():
    print("=" * 60)
    print(" REINICIO DE BASE DE DATOS - ASISTENCIA NURR")
    print("=" * 60)

    # 1. Liberar el pool de conexiones existente
    engine.dispose()

    # 2. Si es SQLite, eliminar el archivo .db directamente si existe
    if settings.DATABASE_URL.startswith("sqlite"):
        db_path = settings.DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")
        # Normalizar ruta relativa o absoluta
        if db_path.startswith("./") or db_path.startswith(".\\"):
            db_path = db_path[2:]

        if os.path.exists(db_path):
            try:
                os.remove(db_path)
                print(f"[*] Archivo de base de datos '{db_path}' eliminado.")
            except Exception as e:
                print(f"[!] No se pudo eliminar el archivo directamente ({e}). Limpiando tablas...")
                Base.metadata.drop_all(bind=engine)
        else:
            print(f"[*] Base de datos '{db_path}' no existía previamente.")
    else:
        print("[*] Eliminando todas las tablas existentes...")
        Base.metadata.drop_all(bind=engine)

    # 3. Aplicar migraciones con Alembic
    print("[*] Aplicando migraciones de Alembic (upgrade head)...")
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    print("[+] Esquema de base de datos creado exitosamente.")

    # 4. Sembrado de datos maestros
    print("[*] Sembrando datos maestros iniciales...")
    seed_database()

    print("=" * 60)
    print(" ¡BASE DE DATOS REINICIADA Y LISTA DESDE CERO!")
    print(" Usuario Administrador: V-00000000")
    print(" Contraseña:             admin1234")
    print(" URL del Prototipo:      http://localhost:8000/static/")
    print("=" * 60)

if __name__ == "__main__":
    reset_database()
