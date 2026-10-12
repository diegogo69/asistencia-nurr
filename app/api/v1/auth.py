from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.api.deps import get_current_user, get_current_admin
from app.models.usuario import Usuario
from app.schemas.auth import LoginRequest, TokenResponse, UserProfileResponse

router = APIRouter(prefix="/auth", tags=["Autenticación Administrativa"])

def format_user_profile(user: Usuario) -> UserProfileResponse:
    return UserProfileResponse(
        id=user.id,
        documento_identidad=user.documento_identidad,
        nombre=user.nombre,
        apellido=user.apellido,
        nombre_completo=user.nombre_completo,
        rol_id=user.rol_id,
        rol=user.rol.nombre if user.rol else "Sin rol",
        departamento_id=user.departamento_id,
        departamento=user.departamento.nombre if user.departamento else "Sin departamento",
        requiere_password=user.rol.requiere_password if user.rol else False
    )

@router.post("/login", response_model=TokenResponse, summary="Iniciar sesión administrativa")
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Autentica a un usuario administrativo (Coordinador/Administrador) y emite un token JWT."""
    # 1. Buscar usuario por documento de identidad
    usuario = db.query(Usuario).filter(Usuario.documento_identidad == login_data.documento_identidad).first()
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
        user=format_user_profile(usuario)
    )

@router.get("/me", response_model=UserProfileResponse, summary="Obtener perfil del usuario autenticado")
def get_me(current_user: Usuario = Depends(get_current_user)):
    """Retorna los datos del perfil del usuario actualmente autenticado."""
    return format_user_profile(current_user)

@router.post("/logout", summary="Cerrar sesión")
def logout(current_user: Usuario = Depends(get_current_user)):
    """Invalida la sesión activa en el cliente."""
    return {"message": "Sesión cerrada exitosamente."}
