import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_password_hash
from app.core.documento import format_documento_identidad
from app.api.deps import get_current_user, get_current_admin
from app.models.usuario import Usuario
from app.schemas.auth import (
    LoginRequest, TokenResponse, UserProfileResponse,
    PrimerIngresoRequest, CambiarPasswordRequest,
    RecuperarPasswordSolicitud, VerificarTokenRequest, RestablecerPasswordRequest
)
from app.services.email_service import send_password_reset_email, mask_email

router = APIRouter(prefix="/auth", tags=["Autenticación Administrativa"])

def format_user_profile(user: Usuario) -> UserProfileResponse:
    return UserProfileResponse(
        id=user.id,
        documento_identidad=user.documento_identidad,
        email=user.email,
        nombre=user.nombre,
        apellido=user.apellido,
        nombre_completo=user.nombre_completo,
        rol_id=user.rol_id,
        rol=user.rol.nombre if user.rol else "Sin rol",
        departamento_id=user.departamento_id,
        departamento=user.departamento.nombre if user.departamento else "Sin departamento",
        requiere_password=user.rol.requiere_password if user.rol else False,
        debe_cambiar_password=user.debe_cambiar_password
    )

@router.post("/login", response_model=TokenResponse, summary="Iniciar sesión administrativa")
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Autentica a un usuario administrativo (Coordinador/Administrador) y emite un token JWT."""
    # 1. Buscar usuario por documento de identidad
    usuario = db.query(Usuario).filter(func.lower(Usuario.documento_identidad) == login_data.documento_identidad.lower()).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de acceso inválidas."
        )

    # 2. Verificar estado de la cuenta
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Su cuenta se encuentra inhabilitada. Contacte al administrador."
        )

    # 3. Verificar privilegios de gestión
    if not usuario.rol or not usuario.rol.requiere_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no cuenta con privilegios para acceder al panel de gestión."
        )

    # 4. Verificar contraseña con Bcrypt
    if not verify_password(login_data.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de acceso inválidas."
        )

    # 5. Generar token JWT
    token_payload = {
        "sub": str(usuario.id),
        "doc": usuario.documento_identidad,
        "rol": usuario.rol.nombre,
        "depto": usuario.departamento.nombre if usuario.departamento else None
    }
    access_token = create_access_token(token_payload)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=format_user_profile(usuario),
        debe_cambiar_password=usuario.debe_cambiar_password
    )

@router.post("/primer-ingreso", response_model=TokenResponse, summary="Configuración obligatoria de credenciales y correo en primer inicio")
def primer_ingreso(
    data: PrimerIngresoRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Permite al usuario administrador registrar su correo y una nueva contraseña en su primer inicio de sesión."""
    # Verificar que la nueva contraseña no sea la contraseña por defecto
    if data.nuevo_password == "admin1234":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Por razones de seguridad, la nueva contraseña debe ser diferente a la contraseña inicial por defecto."
        )

    # Verificar que el correo electrónico no esté registrado por otro usuario
    existing_email = db.query(Usuario).filter(
        func.lower(Usuario.email) == data.email.lower(),
        Usuario.id != current_user.id
    ).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El correo electrónico '{data.email}' ya se encuentra registrado por otro usuario."
        )

    current_user.email = data.email.strip().lower()
    current_user.password_hash = get_password_hash(data.nuevo_password)
    current_user.debe_cambiar_password = False

    db.commit()
    db.refresh(current_user)

    token_payload = {
        "sub": str(current_user.id),
        "doc": current_user.documento_identidad,
        "rol": current_user.rol.nombre if current_user.rol else "",
        "depto": current_user.departamento.nombre if current_user.departamento else None
    }
    new_token = create_access_token(token_payload)

    return TokenResponse(
        access_token=new_token,
        token_type="bearer",
        user=format_user_profile(current_user),
        debe_cambiar_password=False
    )

@router.post("/cambiar-password", summary="Cambio de contraseña para usuario autenticado")
def cambiar_password(
    data: CambiarPasswordRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Permite al usuario autenticado (con rol de gestión) cambiar su contraseña personal."""
    if not current_user.rol or not current_user.rol.requiere_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El rol asignado a este usuario no requiere ni utiliza contraseña de acceso."
        )

    if not verify_password(data.password_actual, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual suministrada es incorrecta."
        )

    current_user.password_hash = get_password_hash(data.nuevo_password)
    current_user.debe_cambiar_password = False
    db.commit()

    return {"message": "Contraseña actualizada exitosamente."}

@router.post("/recuperar-password/solicitar", summary="Solicitar mensaje de recuperación de contraseña")
def solicitar_recuperacion_password(
    data: RecuperarPasswordSolicitud,
    db: Session = Depends(get_db)
):
    """Busca al usuario por cédula o correo electrónico y envía un mensaje de recuperación con token de seguridad."""
    ident = data.identificador.strip()
    usuario = None

    if "@" in ident:
        usuario = db.query(Usuario).filter(func.lower(Usuario.email) == ident.lower()).first()
    else:
        try:
            doc_clean = format_documento_identidad(ident)
            usuario = db.query(Usuario).filter(func.lower(Usuario.documento_identidad) == doc_clean.lower()).first()
        except ValueError:
            usuario = db.query(Usuario).filter(func.lower(Usuario.documento_identidad) == ident.lower()).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró ningún usuario registrado con el identificador suministrado."
        )

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta se encuentra inhabilitada. Contacte al administrador del sistema."
        )

    if not usuario.rol or not usuario.rol.requiere_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este usuario no utiliza contraseña de acceso. Su autenticación es exclusivamente biométrica en el kiosco."
        )

    if not usuario.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario no tiene un correo electrónico registrado para el envío del mensaje de recuperación. Contacte al administrador."
        )

    reset_token = secrets.token_urlsafe(32)
    usuario.reset_password_token = reset_token
    usuario.reset_password_expires = datetime.now(timezone.utc) + timedelta(minutes=30)
    db.commit()

    # Enviar correo de recuperación
    send_password_reset_email(
        to_email=usuario.email,
        nombre_usuario=usuario.nombre_completo,
        reset_token=reset_token,
        expires_minutes=30
    )

    return {
        "message": "Se ha enviado un mensaje de recuperación con las instrucciones a su correo electrónico registrado.",
        "email_enmascarado": mask_email(usuario.email),
        "reset_token": reset_token
    }

@router.post("/recuperar-password/verificar", summary="Verificar validez de token de recuperación")
def verificar_token_recuperacion(
    data: VerificarTokenRequest,
    db: Session = Depends(get_db)
):
    """Verifica si el token de recuperación proporcionado es válido y no ha expirado."""
    usuario = db.query(Usuario).filter(Usuario.reset_password_token == data.token.strip()).first()
    if not usuario or not usuario.reset_password_expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El token de recuperación es inválido o no existe."
        )

    exp = usuario.reset_password_expires
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)

    if exp < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El token de recuperación ha expirado. Solicite un nuevo mensaje de recuperación."
        )

    return {
        "valido": True,
        "documento_identidad": usuario.documento_identidad,
        "nombre_completo": usuario.nombre_completo,
        "email_enmascarado": mask_email(usuario.email or "")
    }

@router.post("/recuperar-password/restablecer", summary="Restablecer contraseña con token de recuperación")
def restablecer_password(
    data: RestablecerPasswordRequest,
    db: Session = Depends(get_db)
):
    """Restablece la contraseña del usuario utilizando el token válido enviado por correo electrónico."""
    usuario = db.query(Usuario).filter(Usuario.reset_password_token == data.token.strip()).first()
    if not usuario or not usuario.reset_password_expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El token de recuperación es inválido o no existe."
        )

    exp = usuario.reset_password_expires
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)

    if exp < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El token de recuperación ha expirado. Solicite un nuevo mensaje de recuperación."
        )

    usuario.password_hash = get_password_hash(data.nuevo_password)
    usuario.debe_cambiar_password = False
    usuario.reset_password_token = None
    usuario.reset_password_expires = None
    db.commit()

    return {"message": "Contraseña restablecida exitosamente. Ahora puede iniciar sesión con sus nuevas credenciales."}

@router.get("/me", response_model=UserProfileResponse, summary="Obtener perfil del usuario autenticado")
def get_me(current_user: Usuario = Depends(get_current_user)):
    """Retorna los datos del perfil del usuario actualmente autenticado."""
    return format_user_profile(current_user)

@router.post("/logout", summary="Cerrar sesión")
def logout(current_user: Usuario = Depends(get_current_user)):
    """Invalida la sesión activa en el cliente."""
    return {"message": "Sesión cerrada exitosamente."}
