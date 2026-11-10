import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.logging_config import setup_logging, get_logs_dir
from app.api.v1.api import api_router

# Inicializar sistema de logs en logs/
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Evento de inicio del servidor
    logger.info("=" * 60)
    logger.info(f" INICIANDO SERVIDOR: {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f" Directorio de logs: {get_logs_dir().resolve()}")
    logger.info(f" URL de Base de Datos: {settings.DATABASE_URL}")
    logger.info("=" * 60)
    yield
    # Evento de parada del servidor
    logger.info("=" * 60)
    logger.info(f" DETENIENDO SERVIDOR: {settings.PROJECT_NAME} (Apagado ordenado)")
    logger.info("=" * 60)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API RESTful para el Sistema de Asistencia de la Unidad de Soporte Técnico ULA-NURR",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware de registro de peticiones HTTP en logs/asistencia.log
@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    client_ip = request.client.host if request.client else "desconocido"
    path = request.url.path
    method = request.method

    try:
        response = await call_next(request)
        process_time = (time.perf_counter() - start_time) * 1000.0
        # No inundar logs con llamadas excesivas de health check si se desea, pero registrar con nivel DEBUG o INFO moderado
        if path == "/api/health":
            logger.debug(f"{method} {path} - {response.status_code} ({process_time:.1f}ms) [{client_ip}]")
        else:
            logger.info(f"{method} {path} - {response.status_code} ({process_time:.1f}ms) [{client_ip}]")
        return response
    except Exception as exc:
        process_time = (time.perf_counter() - start_time) * 1000.0
        logger.error(f"ERROR en {method} {path} ({process_time:.1f}ms) [{client_ip}]: {exc}", exc_info=True)
        raise exc


# Registrar enrutadores de la API v1
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/api/health", tags=["Salud"])
def health_check():
    """Endpoint de comprobación de salud del sistema."""
    return {
        "status": "online",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "https_enabled": True,
        "logs_dir": str(get_logs_dir().resolve()),
    }


# Montar archivos estáticos del prototipo para pruebas y visualización web
def resolve_prototipo_dir() -> str:
    # 1. Empaquetado PyInstaller
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass_proto = os.path.join(sys._MEIPASS, "prototipo")
        if os.path.exists(meipass_proto):
            return meipass_proto

    # 2. Junto al ejecutable
    if getattr(sys, "frozen", False):
        exe_proto = os.path.join(os.path.dirname(sys.executable), "prototipo")
        if os.path.exists(exe_proto):
            return exe_proto

    # 3. Directorio del código fuente del proyecto
    source_proto = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "prototipo"))
    if os.path.exists(source_proto):
        return source_proto

    return ""


prototipo_dir = resolve_prototipo_dir()
if prototipo_dir and os.path.exists(prototipo_dir):
    app.mount("/static", StaticFiles(directory=prototipo_dir, html=True), name="static")

    @app.get("/", include_in_schema=False)
    def root_redirect():
        return RedirectResponse(url="/static/index.html")
