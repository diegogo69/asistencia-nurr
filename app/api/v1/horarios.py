from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models.horario import HorarioPlantilla, HorarioDetalle, TipoHorario
from app.models.usuario import Usuario
from app.schemas.horario import (
    HorarioPlantillaCreate, HorarioPlantillaUpdate,
    HorarioPlantillaResponse, HorarioPlantillaListResponse,
    HorarioDetalleResponse
)

router = APIRouter(prefix="/horarios", tags=["Gestión de Horarios"])

def format_horario_response(h: HorarioPlantilla, user_count: int = 0) -> HorarioPlantillaResponse:
    detalles = [
        HorarioDetalleResponse(
            id=d.id,
            dia_semana=d.dia_semana,
            hora_entrada=d.hora_entrada,
            hora_salida=d.hora_salida
        )
        for d in h.detalles
    ]
    return HorarioPlantillaResponse(
        id=h.id,
        nombre=h.nombre,
        tipo=h.tipo,
        horas_requeridas=h.horas_requeridas or 0,
        detalles=detalles,
        total_usuarios=user_count
    )

@router.get("", response_model=HorarioPlantillaListResponse, summary="Listar plantillas de horario")
def list_horarios(
    q: Optional[str] = Query(None, description="Búsqueda por nombre"),
    tipo: Optional[TipoHorario] = Query(None, description="Filtrar por tipo (fijo/flexible)"),
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(10, ge=1, le=500, description="Elementos por página"),
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    query = db.query(HorarioPlantilla)
    if q:
        query = query.filter(HorarioPlantilla.nombre.ilike(f"%{q.strip()}%"))
    if tipo:
        query = query.filter(HorarioPlantilla.tipo == tipo)

    total = query.count()
    total_pages = ceil(total / limit) if total > 0 else 1

    items_raw = query.order_by(HorarioPlantilla.nombre.asc()).offset((page - 1) * limit).limit(limit).all()

    items = []
    for h in items_raw:
        user_count = db.query(func.count(Usuario.id)).filter(Usuario.horario_id == h.id).scalar()
        items.append(format_horario_response(h, user_count or 0))

    return HorarioPlantillaListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )

@router.get("/{id}", response_model=HorarioPlantillaResponse, summary="Obtener una plantilla de horario")
def get_horario(
    id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    horario = db.query(HorarioPlantilla).filter(HorarioPlantilla.id == id).first()
    if not horario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla de horario no encontrada.")
    user_count = db.query(func.count(Usuario.id)).filter(Usuario.horario_id == id).scalar()
    return format_horario_response(horario, user_count or 0)

@router.post("", response_model=HorarioPlantillaResponse, status_code=status.HTTP_201_CREATED, summary="Crear plantilla de horario")
def create_horario(
    data: HorarioPlantillaCreate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    # 1. Validar no duplicidad de nombre
    existing = db.query(HorarioPlantilla).filter(func.lower(HorarioPlantilla.nombre) == data.nombre.strip().lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una plantilla de horario con el nombre '{data.nombre}'."
        )

    # 2. Validar coherencia según tipo
    if data.tipo == TipoHorario.FIJO:
        if not data.detalles or len(data.detalles) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Una plantilla de horario fijo debe incluir al menos un bloque diario de entrada y salida."
            )
    elif data.tipo == TipoHorario.FLEXIBLE:
        if not data.horas_requeridas or data.horas_requeridas <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Una plantilla de horario flexible debe especificar la cantidad mínima de horas requeridas por semana."
            )

    nueva_plantilla = HorarioPlantilla(
        nombre=data.nombre.strip(),
        tipo=data.tipo,
        horas_requeridas=data.horas_requeridas if data.tipo == TipoHorario.FLEXIBLE else 0
    )
    db.add(nueva_plantilla)
    db.flush()

    if data.tipo == TipoHorario.FIJO and data.detalles:
        for det in data.detalles:
            nuevo_detalle = HorarioDetalle(
                horario_plantilla_id=nueva_plantilla.id,
                dia_semana=det.dia_semana,
                hora_entrada=det.hora_entrada,
                hora_salida=det.hora_salida
            )
            db.add(nuevo_detalle)

    db.commit()
    db.refresh(nueva_plantilla)
    return format_horario_response(nueva_plantilla, 0)

@router.put("/{id}", response_model=HorarioPlantillaResponse, summary="Actualizar plantilla de horario")
def update_horario(
    id: int,
    data: HorarioPlantillaUpdate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    horario = db.query(HorarioPlantilla).filter(HorarioPlantilla.id == id).first()
    if not horario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla de horario no encontrada.")

    if data.nombre is not None:
        nuevo_nombre = data.nombre.strip()
        existing = db.query(HorarioPlantilla).filter(
            func.lower(HorarioPlantilla.nombre) == nuevo_nombre.lower(),
            HorarioPlantilla.id != id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe otra plantilla de horario con el nombre '{nuevo_nombre}'."
            )
        horario.nombre = nuevo_nombre

    if data.tipo is not None:
        horario.tipo = data.tipo

    if data.horas_requeridas is not None:
        horario.horas_requeridas = data.horas_requeridas

    # Actualizar bloques si fueron enviados
    if data.detalles is not None:
        # Eliminar detalles previos
        db.query(HorarioDetalle).filter(HorarioDetalle.horario_plantilla_id == id).delete()
        for det in data.detalles:
            nuevo_detalle = HorarioDetalle(
                horario_plantilla_id=id,
                dia_semana=det.dia_semana,
                hora_entrada=det.hora_entrada,
                hora_salida=det.hora_salida
            )
            db.add(nuevo_detalle)

    db.commit()
    db.refresh(horario)
    user_count = db.query(func.count(Usuario.id)).filter(Usuario.horario_id == id).scalar()
    return format_horario_response(horario, user_count or 0)

@router.delete("/{id}", summary="Eliminar plantilla de horario")
def delete_horario(
    id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    horario = db.query(HorarioPlantilla).filter(HorarioPlantilla.id == id).first()
    if not horario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla de horario no encontrada.")

    # Verificar si tiene usuarios asignados
    users_attached = db.query(Usuario).filter(Usuario.horario_id == id).count()
    if users_attached > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede eliminar la plantilla porque está asignada a {users_attached} usuario(s). Reasigne su horario antes de proceder."
        )

    db.delete(horario)
    db.commit()
    return {"message": f"Plantilla de horario '{horario.nombre}' eliminada exitosamente."}
