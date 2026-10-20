from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
from app.core.documento import format_documento_identidad

class LoginRequest(BaseModel):
    documento_identidad: str = Field(..., description="Cédula de identidad o pasaporte del usuario")
    password: str = Field(..., min_length=4, description="Contraseña en texto plano")

    @field_validator("documento_identidad", mode="before")
    @classmethod
    def validate_and_format_documento(cls, v: Any) -> str:
        if not v:
            raise ValueError("El documento de identidad es requerido.")
        return format_documento_identidad(str(v))

class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    documento_identidad: str
    nombre: str
    apellido: str
    nombre_completo: str
    rol_id: int
    rol: str
    departamento_id: int
    departamento: str
    requiere_password: bool

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse
