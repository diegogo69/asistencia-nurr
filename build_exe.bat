@echo off
chcp 65001 > nul
title Compilador AsistenciaNURR (Windows 10)

echo ========================================================
echo    COMPILADOR DE EJECUTABLE WINDOWS 10 - ASISTENCIA-NURR
echo ========================================================
echo.

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

python build_exe.py

pause
