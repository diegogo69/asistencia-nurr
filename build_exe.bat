@echo off
chcp 65001 > nul
title Compilador de Ejecutable Asistencia-NURR para Windows 10

echo ========================================================
echo    COMPILADOR DE EJECUTABLE ASISTENCIA-NURR (WIN 10)
echo             Unidad de Soporte Técnico ULA-NURR
echo ========================================================
echo.

set "CSC_EXE=C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC_EXE%" (
    set "CSC_EXE=C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe"
)

if not exist "%CSC_EXE%" (
    echo [!] No se encontro el compilador de C# (csc.exe) de .NET Framework en Windows.
    echo [*] Verifique la instalacion de .NET Framework 4.5 o superior.
    pause
    exit /b 1
)

echo [*] Compilando AsistenciaNURR.exe con subsistema Windows GUI (sin consola visible)...
echo [*] Incrustando manifiesto de compatibilidad Windows 10/11 y soporte High-DPI...

"%CSC_EXE%" /nologo /target:winexe /platform:anycpu /win32manifest:app.manifest /optimize+ /out:AsistenciaNURR.exe launcher.cs

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [+] ========================================================
    echo [+] COMPILACION COMPLETADA EXITOSAMENTE
    echo [+] Archivo generado: AsistenciaNURR.exe
    echo [+] Compatible con:  Windows 10 y Windows 11 (64-bit y 32-bit)
    echo [+] Consola visible:  NO (Subsistema GUI nativo)
    echo [+] Interfaz Admin:   SI (Panel de Control + Perfil Web)
    echo [+] Carpeta de logs:  logs\
    echo [+] ========================================================
) else (
    echo.
    echo [!] Ocurrio un error durante la compilacion. Codigo de salida: %ERRORLEVEL%
)

echo.
pause
