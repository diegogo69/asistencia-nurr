import json
from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.security import get_password_hash
from app.api.deps import get_current_admin
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.departamento import Departamento
from app.models.horario import HorarioPlantilla
from app.models.asistencia import Asistencia
from app.schemas.usuario import (
    UsuarioCreate, UsuarioUpdate, UsuarioResponse,
    UsuarioListResponse, CheckDocumentoResponse, BiometriaEnrollRequest
)
from app.services.qr_service import (
    generate_unique_qr_code,
    generate_qr_image_bytes,
    generate_credencial_pdf
)

router = APIRouter(prefix="/usuarios", tags=["Gestión de Usuarios"])

def format_usuario_response(u: Usuario) -> UsuarioResponse:
    return UsuarioResponse(
        id=u.id,
        documento_identidad=u.documento_identidad,
        nombre=u.nombre,
        apellido=u.apellido,
        nombre_completo=u.nombre_completo,
        rol_id=u.rol_id,
        rol=u.rol.nombre if u.rol else "Sin rol",
        departamento_id=u.departamento_id,
        departamento=u.departamento.nombre if u.departamento else "Sin departamento",
        horario_id=u.horario_id,
        horario=u.horario.nombre if u.horario else None,
        tiene_biometria=bool(u.vector_biometrico),
        codigo_qr=u.codigo_qr,
        tiene_password=bool(u.password_hash),
        activo=u.activo
    )

@router.get("/check-documento", response_model=CheckDocumentoResponse, summary="Validar unicidad de documento de identidad (onBlur)")
def check_documento(
    documento: str = Query(..., min_length=4, description="Documento a consultar"),
    exclude_id: Optional[int] = Query(None, description="ID de usuario a excluir en edición"),
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    query = db.query(Usuario).filter(func.lower(Usuario.documento_identidad) == documento.strip().lower())
    if exclude_id:
        query = query.filter(Usuario.id != exclude_id)
    existing = query.first()

    if existing:
        return CheckDocumentoResponse(
            disponible=False,
            documento_identidad=documento.strip(),
            mensaje="El documento de identidad ingresado ya se encuentra registrado en la plataforma."
        )
    return CheckDocumentoResponse(
        disponible=True,
        documento_identidad=documento.strip(),
        mensaje="Documento de identidad disponible para registro."
    )

@router.get("/roles/all", summary="Listar roles del sistema")
def list_roles(
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    roles = db.query(Rol).order_by(Rol.id.asc()).all()
    return [{"id": r.id, "nombre": r.nombre, "requiere_password": r.requiere_password} for r in roles]

@router.get("", response_model=UsuarioListResponse, summary="Listar usuarios")
def list_usuarios(
    q: Optional[str] = Query(None, description="Búsqueda por documento, nombre o apellido"),
    departamento_id: Optional[int] = Query(None, description="Filtrar por departamento"),
    rol_id: Optional[int] = Query(None, description="Filtrar por rol"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo/inactivo"),
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(10, ge=1, le=500, description="Elementos por página"),
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    query = db.query(Usuario)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            (Usuario.documento_identidad.ilike(term)) |
            (Usuario.nombre.ilike(term)) |
            (Usuario.apellido.ilike(term))
        )
    if departamento_id:
        query = query.filter(Usuario.departamento_id == departamento_id)
    if rol_id:
        query = query.filter(Usuario.rol_id == rol_id)
    if activo is not None:
        query = query.filter(Usuario.activo == activo)

    total = query.count()
    total_pages = ceil(total / limit) if total > 0 else 1

    users = query.order_by(Usuario.apellido.asc(), Usuario.nombre.asc()).offset((page - 1) * limit).limit(limit).all()
    items = [format_usuario_response(u) for u in users]

    return UsuarioListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )

@router.get("/{id}", response_model=UsuarioResponse, summary="Obtener detalle de usuario")
def get_usuario(
    id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    usuario = db.query(Usuario).filter(Usuario.id == id).first()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    return format_usuario_response(usuario)

@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED, summary="Registrar nuevo usuario")
def create_usuario(
    data: UsuarioCreate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    doc_clean = data.documento_identidad.strip().upper()
    existing = db.query(Usuario).filter(func.upper(Usuario.documento_identidad) == doc_clean).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El documento de identidad '{doc_clean}' ya se encuentra registrado."
        )

    # Validar rol y requerimiento de contraseña
    rol = db.query(Rol).filter(Rol.id == data.rol_id).first()
    if not rol:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El rol seleccionado no es válido.")

    password_hash = None
    if rol.requiere_password:
        if not data.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El rol seleccionado requiere obligatoriamente una contraseña de acceso para el panel de gestión."
            )
        password_hash = get_password_hash(data.password)
    elif data.password:
        password_hash = get_password_hash(data.password)

    # Validar departamento y horario
    if not db.query(Departamento).filter(Departamento.id == data.departamento_id).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El departamento seleccionado no existe.")

    if data.horario_id and not db.query(HorarioPlantilla).filter(HorarioPlantilla.id == data.horario_id).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La plantilla de horario seleccionada no existe.")

    # Generar código QR único
    qr_token = generate_unique_qr_code(db)

    nuevo_usuario = Usuario(
        documento_identidad=doc_clean,
        nombre=data.nombre.strip(),
        apellido=data.apellido.strip(),
        rol_id=data.rol_id,
        departamento_id=data.departamento_id,
        horario_id=data.horario_id,
        password_hash=password_hash,
        codigo_qr=qr_token,
        activo=data.activo
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return format_usuario_response(nuevo_usuario)

@router.put("/{id}", response_model=UsuarioResponse, summary="Actualizar usuario")
def update_usuario(
    id: int,
    data: UsuarioUpdate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    usuario = db.query(Usuario).filter(Usuario.id == id).first()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    if data.documento_identidad is not None:
        doc_clean = data.documento_identidad.strip().upper()
        existing = db.query(Usuario).filter(
            func.upper(Usuario.documento_identidad) == doc_clean,
            Usuario.id != id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El documento de identidad '{doc_clean}' ya está en uso por otro usuario."
            )
        usuario.documento_identidad = doc_clean

    if data.nombre is not None:
        usuario.nombre = data.nombre.strip()
    if data.apellido is not None:
        usuario.apellido = data.apellido.strip()
    if data.departamento_id is not None:
        usuario.departamento_id = data.departamento_id
    if data.horario_id is not None:
        usuario.horario_id = data.horario_id
    if data.activo is not None:
        usuario.activo = data.activo

    if data.rol_id is not None:
        rol = db.query(Rol).filter(Rol.id == data.rol_id).first()
        if not rol:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El rol seleccionado no es válido.")
        usuario.rol_id = data.rol_id

    if data.password:
        usuario.password_hash = get_password_hash(data.password)

    db.commit()
    db.refresh(usuario)
    return format_usuario_response(usuario)

@router.patch("/{id}/toggle-status", response_model=UsuarioResponse, summary="Alternar estado activo/inactivo de usuario")
def toggle_usuario_status(
    id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    usuario = db.query(Usuario).filter(Usuario.id == id).first()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    if usuario.id == admin.id and usuario.activo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No puede inhabilitar su propia cuenta activa.")

    usuario.activo = not usuario.activo
    db.commit()
    db.refresh(usuario)
    return format_usuario_response(usuario)

@router.delete("/{id}", summary="Eliminar o desactivar usuario (inmutabilidad)")
def delete_usuario(
    id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    usuario = db.query(Usuario).filter(Usuario.id == id).first()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    if usuario.id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No puede eliminar su propia cuenta activa.")

    # Regla de inmutabilidad: verificar si tiene registros en asistencias
    total_asistencias = db.query(Asistencia).filter(Asistencia.usuario_id == id).count()
    if total_asistencias > 0:
        if not usuario.activo:
            return {
                "tipo_borrado": "inactivo",
                "message": f"El usuario posee {total_asistencias} registros de asistencia históricos. Para preservar la auditoría legal de la institución, no puede ser eliminado físicamente; la cuenta ya se encuentra inhabilitada."
            }
        # Borrado lógico
        usuario.activo = False
        db.commit()
        return {
            "tipo_borrado": "logico",
            "message": f"El usuario posee {total_asistencias} registros de asistencia históricos. Para preservar la auditoría, la cuenta ha sido inhabilitada (borrado lógico)."
        }

    # Borrado físico si no tiene transacciones
    db.delete(usuario)
    db.commit()
    return {
        "tipo_borrado": "fisico",
        "message": f"El usuario '{usuario.nombre_completo}' fue eliminado definitivamente de la base de datos."
    }

@router.post("/{id}/biometria", response_model=UsuarioResponse, summary="Enrolar vector biométrico facial (face-api.js)")
def enroll_biometria(
    id: int,
    data: BiometriaEnrollRequest,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    usuario = db.query(Usuario).filter(Usuario.id == id).first()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    usuario.vector_biometrico = json.dumps(data.vector)
    db.commit()
    db.refresh(usuario)
    return format_usuario_response(usuario)

@router.post("/{id}/regenerar-qr", response_model=UsuarioResponse, summary="Regenerar credencial QR por extravío")
def regenerate_qr(
    id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    usuario = db.query(Usuario).filter(Usuario.id == id).first()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    usuario.codigo_qr = generate_unique_qr_code(db)
    db.commit()
    db.refresh(usuario)
    return format_usuario_response(usuario)

@router.get("/{id}/credencial-qr", summary="Descargar imagen PNG del código QR")
def get_qr_image(
    id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    usuario = db.query(Usuario).filter(Usuario.id == id).first()
    if not usuario or not usuario.codigo_qr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Código QR no disponible para este usuario.")

    img_bytes = generate_qr_image_bytes(usuario.codigo_qr)
    return Response(content=img_bytes, media_type="image/png")

@router.get("/{id}/credencial-pdf", summary="Descargar carnet imprimible en PDF con membrete y QR")
def get_credencial_pdf(
    id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    usuario = db.query(Usuario).filter(Usuario.id == id).first()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    pdf_bytes = generate_credencial_pdf(usuario)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=credencial_{usuario.documento_identidad}.pdf"}
    )
