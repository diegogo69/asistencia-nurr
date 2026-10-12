from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models.asistencia import Asistencia, EstadoCumplimiento
from app.models.departamento import Departamento
from app.models.usuario import Usuario
from app.schemas.reportes import ReporteResumenResponse
from app.services.reports_service import (
    build_attendance_query,
    compute_report_metrics,
    generate_csv_report,
    generate_pdf_report
)

router = APIRouter(prefix="/reportes", tags=["Generación de Reportes"])

@router.get("/resumen", response_model=ReporteResumenResponse, summary="Obtener métricas consolidadas de asistencia")
def get_report_summary(
    fecha_desde: Optional[date] = Query(None, description="Fecha inicial (YYYY-MM-DD)"),
    fecha_hasta: Optional[date] = Query(None, description="Fecha final (YYYY-MM-DD)"),
    usuario_id: Optional[int] = Query(None, description="Filtrar por usuario específico"),
    departamento_id: Optional[int] = Query(None, description="Filtrar por unidad organizacional"),
    estado: Optional[EstadoCumplimiento] = Query(None, description="Filtrar por estado de cumplimiento"),
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    query = build_attendance_query(
        db=db,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        usuario_id=usuario_id,
        departamento_id=departamento_id,
        estado=estado
    )
    records = query.all()
    metrics = compute_report_metrics(records)
    metrics.rango_desde = fecha_desde.strftime("%d/%m/%Y") if fecha_desde else None
    metrics.rango_hasta = fecha_hasta.strftime("%d/%m/%Y") if fecha_hasta else None
    return metrics

@router.get("/exportar/csv", summary="Exportar reporte en formato CSV / Excel")
def export_csv(
    fecha_desde: Optional[date] = Query(None, description="Fecha inicial"),
    fecha_hasta: Optional[date] = Query(None, description="Fecha final"),
    usuario_id: Optional[int] = Query(None, description="Filtrar por usuario"),
    departamento_id: Optional[int] = Query(None, description="Filtrar por departamento"),
    estado: Optional[EstadoCumplimiento] = Query(None, description="Filtrar por estado"),
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    query = build_attendance_query(
        db=db,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        usuario_id=usuario_id,
        departamento_id=departamento_id,
        estado=estado
    )
    records = query.order_by(Asistencia.fecha.asc(), Asistencia.hora_entrada.asc()).all()
    if not records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existen registros disponibles para generar el reporte en el rango especificado."
        )

    csv_bytes = generate_csv_report(records)
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=reporte_asistencia_nurr.csv"}
    )

@router.get("/exportar/pdf", summary="Exportar reporte oficial en PDF con membrete institucional y firma")
def export_pdf(
    fecha_desde: Optional[date] = Query(None, description="Fecha inicial"),
    fecha_hasta: Optional[date] = Query(None, description="Fecha final"),
    usuario_id: Optional[int] = Query(None, description="Filtrar por usuario"),
    departamento_id: Optional[int] = Query(None, description="Filtrar por departamento"),
    estado: Optional[EstadoCumplimiento] = Query(None, description="Filtrar por estado"),
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    query = build_attendance_query(
        db=db,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        usuario_id=usuario_id,
        departamento_id=departamento_id,
        estado=estado
    )
    records = query.order_by(Asistencia.fecha.asc(), Asistencia.hora_entrada.asc()).all()
    if not records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existen registros disponibles para generar el reporte en el rango especificado."
        )

    depto_nombre = None
    if departamento_id:
        depto = db.query(Departamento).filter(Departamento.id == departamento_id).first()
        if depto:
            depto_nombre = depto.nombre

    pdf_bytes = generate_pdf_report(
        asistencias=records,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        depto_nombre=depto_nombre
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=reporte_asistencia_nurr.pdf"}
    )
