from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models.red import RedAutorizada
from app.models.usuario import Usuario
from app.schemas.red import (
    RedAutorizadaCreate, RedAutorizadaUpdate,
    RedAutorizadaResponse, RedAutorizadaListResponse
)

router = APIRouter(prefix="/redes", tags=["Rangos de Red Autorizados"])

@router.get("", response_model=RedAutorizadaListResponse, summary="Listar reglas de red autorizadas")
def list_redes(
    q: Optional[str] = Query(None, description="Búsqueda por IP o descripción"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo/inactivo"),
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(10, ge=1, le=500, description="Elementos por página"),
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    query = db.query(RedAutorizada)
    if q:
        query = query.filter(
            (RedAutorizada.direccion_ip.ilike(f"%{q.strip()}%")) |
            (RedAutorizada.descripcion.ilike(f"%{q.strip()}%"))
        )
    if activo is not None:
        query = query.filter(RedAutorizada.activo == activo)

    total = query.count()
    total_pages = ceil(total / limit) if total > 0 else 1

    items = query.order_by(RedAutorizada.id.asc()).offset((page - 1) * limit).limit(limit).all()

    return RedAutorizadaListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )

@router.get("/{id}", response_model=RedAutorizadaResponse, summary="Obtener una regla de red")
def get_red(
    id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    regla = db.query(RedAutorizada).filter(RedAutorizada.id == id).first()
    if not regla:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regla de red no encontrada.")
    return regla

@router.post("", response_model=RedAutorizadaResponse, status_code=status.HTTP_201_CREATED, summary="Registrar regla de red")
def create_red(
    data: RedAutorizadaCreate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    existing = db.query(RedAutorizada).filter(RedAutorizada.direccion_ip == data.direccion_ip).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La dirección IP o rango '{data.direccion_ip}' ya se encuentra registrado."
        )

    nueva = RedAutorizada(
        direccion_ip=data.direccion_ip,
        descripcion=data.descripcion.strip(),
        activo=data.activo
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

@router.put("/{id}", response_model=RedAutorizadaResponse, summary="Actualizar regla de red")
def update_red(
    id: int,
    data: RedAutorizadaUpdate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    regla = db.query(RedAutorizada).filter(RedAutorizada.id == id).first()
    if not regla:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regla de red no encontrada.")

    if data.direccion_ip is not None:
        existing = db.query(RedAutorizada).filter(
            RedAutorizada.direccion_ip == data.direccion_ip,
            RedAutorizada.id != id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La dirección IP o rango '{data.direccion_ip}' ya está registrada en otra regla."
            )
        regla.direccion_ip = data.direccion_ip

    if data.descripcion is not None:
        regla.descripcion = data.descripcion.strip()

    if data.activo is not None:
        regla.activo = data.activo

    db.commit()
    db.refresh(regla)
    return regla

@router.patch("/{id}/toggle-status", response_model=RedAutorizadaResponse, summary="Activar o desactivar regla de red")
def toggle_status(
    id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    regla = db.query(RedAutorizada).filter(RedAutorizada.id == id).first()
    if not regla:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regla de red no encontrada.")

    regla.activo = not regla.activo
    db.commit()
    db.refresh(regla)
    return regla

@router.delete("/{id}", summary="Eliminar regla de red")
def delete_red(
    id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    regla = db.query(RedAutorizada).filter(RedAutorizada.id == id).first()
    if not regla:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regla de red no encontrada.")

    db.delete(regla)
    db.commit()
    return {"message": f"Regla de red '{regla.direccion_ip}' eliminada exitosamente."}
