"""Script de compilación para generar el ejecutable de Windows 10 para Asistencia-NURR.

Genera un único archivo ejecutable autónomo (.exe) sin consola visible (--noconsole),
con icono institucional, soporte para el servidor FastAPI/Uvicorn, certificados SSL
autofirmados, base de datos SQLite y registro de logs en 'logs/asistencia.log'.
"""

import os
import sys
import shutil
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)


def ensure_icon():
    """Genera el archivo app_icon.ico a partir del logo institucional si no existe."""
    ico_path = os.path.join(BASE_DIR, "app_icon.ico")
    png_path = os.path.join(BASE_DIR, "prototipo", "img", "logo-ula-nurr-azul.png")

    if not os.path.exists(ico_path) and os.path.exists(png_path):
        print("[*] Generando icono institucional app_icon.ico...")
        try:
            from PIL import Image
            img = Image.open(png_path)
            img.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
            print("[+] Icono app_icon.ico generado exitosamente.")
        except Exception as e:
            print(f"[!] Advertencia: No se pudo generar app_icon.ico ({e}). Se compilará sin icono personalizado.")

    return ico_path if os.path.exists(ico_path) else None


def build_executable():
    """Ejecuta PyInstaller para empaquetar AsistenciaNURR en un .exe para Windows 10."""
    print("=" * 65)
    print(" COMPILADOR DE EJECUTABLE WINDOWS 10 - ASISTENCIA-NURR")
    print("=" * 65)

    ico_path = ensure_icon()

    # Directorio dedicado de logs
    logs_dir = os.path.join(BASE_DIR, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    gitkeep_path = os.path.join(logs_dir, ".gitkeep")
    if not os.path.exists(gitkeep_path):
        with open(gitkeep_path, "w", encoding="utf-8") as f:
            f.write("# Logs directory\n")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name=AsistenciaNURR",
        "--clean",
        # Incluir archivos de datos
        "--add-data=prototipo;prototipo",
        "--add-data=alembic.ini;.",
        "--add-data=alembic;alembic",
        # Recolectar paquetes críticos
        "--collect-all=uvicorn",
        "--collect-all=fastapi",
        "--collect-all=starlette",
        "--collect-all=sqlalchemy",
        "--collect-all=alembic",
        "--collect-all=aiosqlite",
        "--collect-all=cryptography",
        "--collect-all=python_multipart",
        "--collect-all=reportlab",
        # Módulos locales ocultos
        "--hidden-import=app",
        "--hidden-import=app.main",
        "--hidden-import=generate_certs",
        "--hidden-import=reset_db",
        "--hidden-import=seed",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=sqlite3",
    ]

    if ico_path:
        cmd.append(f"--icon={ico_path}")
        cmd.append(f"--add-data={ico_path};.")

    cmd.append("launcher.py")

    print("[*] Iniciando compilación con PyInstaller (este proceso puede tardar 1-2 minutos)...")
    print(f"[*] Comando: {' '.join(cmd)}")

    result = subprocess.run(cmd)

    if result.returncode != 0:
        print(f"[!] Error durante la compilación. Código de salida: {result.returncode}")
        sys.exit(result.returncode)

    dist_exe = os.path.join(BASE_DIR, "dist", "AsistenciaNURR.exe")
    root_exe = os.path.join(BASE_DIR, "AsistenciaNURR.exe")

    if os.path.exists(dist_exe):
        print(f"[*] Copiando ejecutable a la raíz del repositorio: {root_exe}")
        shutil.copy2(dist_exe, root_exe)
        exe_size_mb = os.path.getsize(root_exe) / (1024 * 1024)
        print("=" * 65)
        print(f" [✓] ¡EJECUTABLE GENERADO CON ÉXITO!")
        print(f"     Archivo: {root_exe}")
        print(f"     Tamaño:  {exe_size_mb:.2f} MB")
        print(f"     Plataforma: Windows 10 (64-bit)")
        print(f"     Modo: Sin consola visible (GUI minimalista integrada)")
        print("=" * 65)
    else:
        print("[!] No se encontró el archivo generado en dist/AsistenciaNURR.exe")
        sys.exit(1)


if __name__ == "__main__":
    build_executable()
