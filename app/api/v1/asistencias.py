from typing import Optional
from math import ceil
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models.asistencia import Asistencia, EstadoCumplimiento
from app.models.usuario import Usuario
from app.schemas.reportes import HistorialItemResponse, HistorialListResponse
from app.services.reports_service import build_attendance_query, calculate_hours_worked

router = APIRouter(prefix="/asistencias", tags=["Historial de Asistencias"])

def format_historial_item(a: Asistencia) -> HistorialItemResponse:
    hora_salida_str = a.hora_salida.strftime("%I:%M %p") if a.hora_salida else None
    h_trabajadas = calculate_hours_worked(a.hora_entrada, a.hora_salida)
    fue_corregido = len(a.resoluciones) > 0 if a.resoluciones else False

    return HistorialItemResponse(
        id=a.id,
        usuario_id=a.usuario_id,
        documento_identidad=a.usuario.documento_identidad,
        nombre_completo=a.usuario.nombre_completo,
        departamento=a.usuario.departamento.nombre if a.usuario.departamento else "Soporte Técnico",
        rol=a.usuario.rol.nombre if a.usuario.rol else "Personal",
        fecha=a.fecha.strftime("%d/%m/%Y"),
        hora_entrada=a.hora_entrada.strftime("%I:%M %p"),
        hora_salida=hora_salida_str,
        horas_trabajadas=h_trabajadas,
        estado_cumplimiento=a.estado_cumplimiento.value,
        metodo_validacion=a.metodo_validacion.value,
        fue_corregido=fue_corregido
    )

@router.get("/historial", response_model=HistorialListResponse, summary="Consultar historial consolidado de asistencia")
def get_historial(
    fecha_desde: Optional[date] = Query(None, description="Fecha inicial del rango (YYYY-MM-DD)"),
    fecha_hasta: Optional[date] = Query(None, description="Fecha final del rango (YYYY-MM-DD)"),
    usuario_id: Optional[int] = Query(None, description="Filtrar por usuario específico"),
    departamento_id: Optional[int] = Query(None, description="Filtrar por unidad organizacional"),
    estado: Optional[EstadoCumplimiento] = Query(None, description="Filtrar por estado de cumplimiento"),
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(10, ge=1, le=500, description="Elementos por página"),
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    """Consulta histórica centralizada con filtros combinados y paginación en base de datos."""
    query = build_attendance_query(
        db=db,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        usuario_id=usuario_id,
        departamento_id=departamento_id,
        estado=estado
    )

    total = query.count()
    total_pages = ceil(total / limit) if total > 0 else 1

    records = query.order_by(Asistencia.fecha.desc(), Asistencia.hora_entrada.desc()).offset((page - 1) * limit).limit(limit).all()
    items = [format_historial_item(a) for a in records]

    return HistorialListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )
