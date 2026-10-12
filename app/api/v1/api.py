from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.departamentos import router as departamentos_router
from app.api.v1.horarios import router as horarios_router
from app.api.v1.redes import router as redes_router
from app.api.v1.usuarios import router as usuarios_router
from app.api.v1.marcacion import router as marcacion_router
from app.api.v1.auditoria import router as auditoria_router
from app.api.v1.asistencias import router as asistencias_router
from app.api.v1.reportes import router as reportes_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(departamentos_router)
api_router.include_router(horarios_router)
api_router.include_router(redes_router)
api_router.include_router(usuarios_router)
api_router.include_router(marcacion_router)
api_router.include_router(auditoria_router)
api_router.include_router(asistencias_router)
api_router.include_router(reportes_router)
