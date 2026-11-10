import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def get_base_dir() -> Path:
    """Retorna la ruta base del proyecto o del ejecutable."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def get_logs_dir() -> Path:
    """Obtiene y asegura la existencia del directorio de logs."""
    logs_dir = get_base_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def setup_logging() -> logging.Logger:
    """Configura el sistema de registro de logs en el directorio logs/."""
    logs_dir = get_logs_dir()
    app_log_file = logs_dir / "asistencia.log"
    error_log_file = logs_dir / "errores.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler principal con rotación (5 MB, 5 respaldos)
    file_handler = RotatingFileHandler(
        app_log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # Handler exclusivo de errores
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Evitar duplicar handlers si se llama múltiples veces
    existing_paths = {
        getattr(h, "baseFilename", None) for h in root_logger.handlers
    }
    if str(app_log_file.resolve()) not in existing_paths:
        root_logger.addHandler(file_handler)
    if str(error_log_file.resolve()) not in existing_paths:
        root_logger.addHandler(error_handler)

    # Agregar salida a consola únicamente si hay stdout disponible
    if sys.stdout is not None and not any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler)
        for h in root_logger.handlers
    ):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Enlazar loggers de uvicorn y fastapi sin duplicar mensajes en stdout
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lgr = logging.getLogger(logger_name)
        lgr.setLevel(logging.INFO)
        lgr.propagate = False
        lgr_paths = {getattr(h, "baseFilename", None) for h in lgr.handlers}
        if str(app_log_file.resolve()) not in lgr_paths:
            lgr.addHandler(file_handler)
        if str(error_log_file.resolve()) not in lgr_paths:
            lgr.addHandler(error_handler)

    for logger_name in ("fastapi", "asistencia"):
        lgr = logging.getLogger(logger_name)
        lgr.setLevel(logging.INFO)
        lgr.propagate = True

    app_logger = logging.getLogger("asistencia")
    return app_logger


def read_recent_logs(max_lines: int = 100) -> list[str]:
    """Lee las últimas líneas del archivo de log principal."""
    log_file = get_logs_dir() / "asistencia.log"
    if not log_file.exists():
        return []
    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            return [line.rstrip("\r\n") for line in lines[-max_lines:]]
    except Exception:
        return []
