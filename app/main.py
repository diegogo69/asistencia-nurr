import os
import sys
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.api.v1.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API RESTful para el Sistema de Asistencia de la Unidad de Soporte Técnico ULA-NURR",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        "https_enabled": True
    }

# Montar archivos estáticos del prototipo para pruebas y visualización web
candidate_dirs = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "prototipo")),
    os.path.abspath(os.path.join(getattr(sys, "_MEIPASS", ""), "prototipo")) if hasattr(sys, "_MEIPASS") else None,
    os.path.abspath(os.path.join(os.getcwd(), "prototipo")),
]
prototipo_dir = next((d for d in candidate_dirs if d and os.path.exists(d)), None)
if prototipo_dir:
    app.mount("/static", StaticFiles(directory=prototipo_dir, html=True), name="static")

    @app.get("/", include_in_schema=False)
    def root_redirect():
        return RedirectResponse(url="/static/index.html")
