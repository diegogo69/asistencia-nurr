@echo off
chcp 65001 > nul
title Servidor Asistencia-NURR (HTTPS LAN)

echo ========================================================
echo    SISTEMA DE ASISTENCIA AUTOMATIZADA - ULA-NURR
echo             Unidad de Soporte Técnico
echo ========================================================
echo.

if not exist "venv\Scripts\activate.bat" (
    echo [!] No se encontro el entorno virtual en 'venv'.
    echo [*] Creando entorno virtual...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [*] Instalando dependencias desde requirements.txt...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

if not exist "certs\cert.pem" (
    echo [*] Certificados SSL no detectados. Generando certificados locales para LAN...
    python generate_certs.py
)

set "INIT_DB=0"
if not exist "asistencia_nurr.db" (
    set "INIT_DB=1"
) else (
    for %%F in ("asistencia_nurr.db") do (
        if %%~zF EQU 0 set "INIT_DB=1"
    )
)

if "%INIT_DB%"=="1" (
    echo [*] Base de datos no inicializada. Aplicando migraciones y sembrando datos maestros...
    python reset_db.py
)

echo.
echo [*] Iniciando servidor web en modo seguro HTTPS...
echo [i] Acceso local:       https://localhost:8000
echo [i] Acceso desde LAN:   https://0.0.0.0:8000
echo.
echo Presione CTRL+C en esta consola para detener el servidor.
echo --------------------------------------------------------

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile certs/key.pem --ssl-certfile certs/cert.pem --reload

pause
