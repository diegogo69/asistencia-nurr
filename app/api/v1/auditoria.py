from typing import Optional
from math import ceil
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models.asistencia import Asistencia, EstadoCumplimiento
from app.models.asistencia_pendiente import AsistenciaPendiente
from app.models.usuario import Usuario
from app.schemas.auditoria import (
    AsistenciaIncompletaResponse, ListIncompletasResponse,
    ResolverIncidenciaRequest, AsistenciaPendienteResponse,
    ListResolucionesResponse
)
from app.services.audit_service import (
    detect_and_mark_incomplete_attendances,
    resolve_incident
)

router = APIRouter(prefix="/auditoria", tags=["Auditoría y Asistencias Incompletas"])

def format_incompleta(a: Asistencia) -> AsistenciaIncompletaResponse:
    hora_salida_str = a.hora_salida.strftime("%I:%M %p") if a.hora_salida else None
    return AsistenciaIncompletaResponse(
        id=a.id,
        usuario_id=a.usuario_id,
        documento_identidad=a.usuario.documento_identidad,
        nombre_completo=a.usuario.nombre_completo,
        departamento=a.usuario.departamento.nombre if a.usuario.departamento else "Soporte Técnico",
        fecha=a.fecha.strftime("%d/%m/%Y"),
        hora_entrada=a.hora_entrada.strftime("%I:%M %p"),
        hora_salida=hora_salida_str,
        estado_cumplimiento=a.estado_cumplimiento.value,
        ip_registro_entrada=a.ip_registro_entrada
    )

def format_resolucion(r: AsistenciaPendiente) -> AsistenciaPendienteResponse:
    user_afectado = r.asistencia.usuario.nombre_completo if r.asistencia and r.asistencia.usuario else "Usuario desconocido"
    return AsistenciaPendienteResponse(
        id=r.id,
        asistencia_id=r.asistencia_id,
        coordinador_id=r.coordinador_id,
        coordinador_nombre=r.coordinador.nombre_completo if r.coordinador else "Coordinador",
        usuario_afectado=user_afectado,
        fecha_resolucion=r.fecha_resolucion.strftime("%d/%m/%Y %I:%M %p"),
        estado_anterior=r.estado_anterior,
        estado_nuevo=r.estado_nuevo,
        observacion=r.observacion
    )

@router.get("/incompletas", response_model=ListIncompletasResponse, summary="Listar asistencias incompletas o pendientes")
def list_incompletas(
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(10, ge=1, le=500, description="Elementos por página"),
    fecha_desde: Optional[date] = Query(None, description="Fecha inicial del rango (YYYY-MM-DD)"),
    fecha_hasta: Optional[date] = Query(None, description="Fecha final del rango (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    """Retorna las marcaciones irregulares que tienen hora de salida nula o están en estado incompleto o pendiente."""
    query = db.query(Asistencia).filter(
        or_(
            Asistencia.hora_salida.is_(None),
            Asistencia.estado_cumplimiento.in_([EstadoCumplimiento.INCOMPLETO, EstadoCumplimiento.PENDIENTE])
        )
    )

    if fecha_desde:
        query = query.filter(Asistencia.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Asistencia.fecha <= fecha_hasta)

    total = query.count()
    total_pages = ceil(total / limit) if total > 0 else 1

    records = query.order_by(Asistencia.fecha.desc(), Asistencia.hora_entrada.desc()).offset((page - 1) * limit).limit(limit).all()
    items = [format_incompleta(a) for a in records]

    return ListIncompletasResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )

@router.post("/resolver", summary="Resolver incidencia de marcación irregular")
def resolver_incidencia(
    data: ResolverIncidenciaRequest,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    """Registra formalmente la corrección manual del Coordinador con bitácora inalterable."""
    if len(data.observacion.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La observación explicativa es obligatoria (mínimo 10 caracteres) para justificar la resolución."
        )

    try:
        asistencia, resolucion = resolve_incident(
            db=db,
            coordinador_id=admin.id,
            asistencia_id=data.asistencia_id,
            hora_salida=data.hora_salida,
            nuevo_estado=data.nuevo_estado,
            observacion=data.observacion
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {
        "message": "Inconsistencia resuelta y registrada en auditoría exitosamente.",
        "asistencia": format_incompleta(asistencia),
        "resolucion_id": resolucion.id
    }

@router.get("/resoluciones", response_model=ListResolucionesResponse, summary="Consultar bitácora de auditoría histórica")
def list_resoluciones(
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(10, ge=1, le=500, description="Elementos por página"),
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    """Consulta los registros inmutables de auditoría de modificaciones efectuadas por la Coordinación."""
    query = db.query(AsistenciaPendiente)
    total = query.count()
    total_pages = ceil(total / limit) if total > 0 else 1

    records = query.order_by(AsistenciaPendiente.fecha_resolucion.desc()).offset((page - 1) * limit).limit(limit).all()
    items = [format_resolucion(r) for r in records]

    return ListResolucionesResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )

@router.post("/ejecutar-deteccion", summary="Disparar detección automática de marcaciones incompletas")
def trigger_detection(
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    """Dispara el proceso de escaneo para marcar como 'incompletas' las entradas sin salida de jornadas previas."""
    marcadas = detect_and_mark_incomplete_attendances(db)
    return {
        "status": "completado",
        "registros_marcados_incompletos": marcadas,
        "timestamp": datetime.now().isoformat()
    }
