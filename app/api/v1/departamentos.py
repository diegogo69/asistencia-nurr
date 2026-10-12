from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models.departamento import Departamento, TipoDepartamento
from app.models.usuario import Usuario
from app.schemas.departamento import (
    DepartamentoCreate, DepartamentoUpdate,
    DepartamentoResponse, DepartamentoListResponse
)

router = APIRouter(prefix="/departamentos", tags=["Unidades Organizacionales"])

@router.get("", response_model=DepartamentoListResponse, summary="Listar unidades organizacionales")
def list_departamentos(
    q: Optional[str] = Query(None, description="Búsqueda por nombre"),
    tipo: Optional[TipoDepartamento] = Query(None, description="Filtrar por tipo"),
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(10, ge=1, le=500, description="Elementos por página"),
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    query = db.query(Departamento)
    if q:
        query = query.filter(Departamento.nombre.ilike(f"%{q.strip()}%"))
    if tipo:
        query = query.filter(Departamento.tipo == tipo)

    total = query.count()
    total_pages = ceil(total / limit) if total > 0 else 1

    items_raw = query.order_by(Departamento.nombre.asc()).offset((page - 1) * limit).limit(limit).all()

    items = []
    for d in items_raw:
        user_count = db.query(func.count(Usuario.id)).filter(Usuario.departamento_id == d.id).scalar()
        items.append(DepartamentoResponse(
            id=d.id,
            nombre=d.nombre,
            tipo=d.tipo,
            total_usuarios=user_count or 0
        ))

    return DepartamentoListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )

@router.get("/{id}", response_model=DepartamentoResponse, summary="Obtener una unidad organizacional")
def get_departamento(
    id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    depto = db.query(Departamento).filter(Departamento.id == id).first()
    if not depto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unidad organizacional no encontrada.")
    user_count = db.query(func.count(Usuario.id)).filter(Usuario.departamento_id == id).scalar()
    return DepartamentoResponse(
        id=depto.id,
        nombre=depto.nombre,
        tipo=depto.tipo,
        total_usuarios=user_count or 0
    )

@router.post("", response_model=DepartamentoResponse, status_code=status.HTTP_201_CREATED, summary="Crear unidad organizacional")
def create_departamento(
    data: DepartamentoCreate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    # Validar no duplicidad de nombre
    existing = db.query(Departamento).filter(func.lower(Departamento.nombre) == data.nombre.strip().lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una unidad organizacional registrada con el nombre '{data.nombre}'."
        )

    nuevo = Departamento(
        nombre=data.nombre.strip(),
        tipo=data.tipo
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return DepartamentoResponse(
        id=nuevo.id,
        nombre=nuevo.nombre,
        tipo=nuevo.tipo,
        total_usuarios=0
    )

@router.put("/{id}", response_model=DepartamentoResponse, summary="Actualizar unidad organizacional")
def update_departamento(
    id: int,
    data: DepartamentoUpdate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    depto = db.query(Departamento).filter(Departamento.id == id).first()
    if not depto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unidad organizacional no encontrada.")

    if data.nombre is not None:
        nuevo_nombre = data.nombre.strip()
        existing = db.query(Departamento).filter(
            func.lower(Departamento.nombre) == nuevo_nombre.lower(),
            Departamento.id != id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe otra unidad organizacional con el nombre '{nuevo_nombre}'."
            )
        depto.nombre = nuevo_nombre

    if data.tipo is not None:
        depto.tipo = data.tipo

    db.commit()
    db.refresh(depto)

    user_count = db.query(func.count(Usuario.id)).filter(Usuario.departamento_id == id).scalar()
    return DepartamentoResponse(
        id=depto.id,
        nombre=depto.nombre,
        tipo=depto.tipo,
        total_usuarios=user_count or 0
    )

@router.delete("/{id}", summary="Eliminar unidad organizacional")
def delete_departamento(
    id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    depto = db.query(Departamento).filter(Departamento.id == id).first()
    if not depto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unidad organizacional no encontrada.")

    # Verificar si posee usuarios vinculados
    users_attached = db.query(Usuario).filter(Usuario.departamento_id == id).count()
    if users_attached > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede eliminar la unidad porque tiene {users_attached} usuario(s) vinculados. Reasigne los usuarios antes de proceder."
        )

    db.delete(depto)
    db.commit()
    return {"message": f"Unidad organizacional '{depto.nombre}' eliminada exitosamente."}
