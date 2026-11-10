import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import get_current_admin
from app.core.config import settings
from app.core.logging_config import get_logs_dir, read_recent_logs
from app.models.usuario import Usuario

router = APIRouter(prefix="/sistema", tags=["Gestión del Sistema y Servidor"])
logger = logging.getLogger("asistencia.sistema")

START_TIME = datetime.now(timezone.utc)


class ShutdownResponse(BaseModel):
    status: str
    message: str
    timestamp: str
    detenido_por: str


class ServerStatusResponse(BaseModel):
    status: str
    app: str
    version: str
    uptime_seconds: float
    pid: int
    logs_dir: str
    https_enabled: bool
    inicio_utc: str


@router.get("/estado", response_model=ServerStatusResponse, summary="Obtener estado del servidor")
def get_server_status(
    current_admin: Usuario = Depends(get_current_admin),
):
    """Retorna métricas y estado del servidor para el perfil de administrador."""
    uptime = (datetime.now(timezone.utc) - START_TIME).total_seconds()
    return ServerStatusResponse(
        status="online",
        app=settings.PROJECT_NAME,
        version=settings.VERSION,
        uptime_seconds=round(uptime, 2),
        pid=os.getpid(),
        logs_dir=str(get_logs_dir().resolve()),
        https_enabled=True,
        inicio_utc=START_TIME.isoformat(),
    )


@router.post("/detener", response_model=ShutdownResponse, summary="Detener la ejecución del servidor")
def shutdown_server(
    current_admin: Usuario = Depends(get_current_admin),
):
    """Detiene la ejecución del servidor web de forma ordenada desde el perfil de administrador.

    Permite finalizar la aplicación cuando la consola de comandos se encuentra oculta.
    """
    admin_info = f"{current_admin.nombre_completo} (ID: {current_admin.documento_identidad}, Rol: {current_admin.rol.nombre if current_admin.rol else 'Admin'})"
    logger.warning(
        f"[!] Solicitud de apagado del servidor recibida desde la interfaz web por el administrador: {admin_info}"
    )

    def delayed_shutdown():
        # Esperar brevemente para permitir que la respuesta HTTP 200 sea enviada al navegador
        time.sleep(1.0)
        logger.info("=" * 60)
        logger.info(f" DETENIENDO SERVIDOR: {settings.PROJECT_NAME} (Apagado ordenado por administrador)")
        logger.info("=" * 60)
        for handler in logging.getLogger().handlers:
            try:
                handler.flush()
            except Exception:
                pass

        # Enviar señal de terminación limpia al proceso actual
        try:
            os.kill(os.getpid(), signal.SIGINT)
        except Exception as e:
            logger.error(f"[!] Error al enviar señal SIGINT ({e}). Finalizando con SIGTERM / os._exit...")
            try:
                os.kill(os.getpid(), signal.SIGTERM)
            except Exception:
                os._exit(0)

    thread = threading.Thread(target=delayed_shutdown, name="ShutdownThread", daemon=True)
    thread.start()

    return ShutdownResponse(
        status="deteniendo",
        message="El servidor de la aplicación se está deteniendo de forma segura.",
        timestamp=datetime.now(timezone.utc).isoformat(),
        detenido_por=admin_info,
    )


@router.get("/logs", summary="Obtener registros recientes de la aplicación")
def get_logs(
    lineas: int = 80,
    current_admin: Usuario = Depends(get_current_admin),
):
    """Retorna los últimos registros generados por la aplicación."""
    recent_logs = read_recent_logs(max_lines=lineas)
    return {
        "total_lineas": len(recent_logs),
        "logs": recent_logs,
        "logs_path": str((get_logs_dir() / "asistencia.log").resolve()),
    }
