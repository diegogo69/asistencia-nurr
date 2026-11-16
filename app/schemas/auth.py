import re
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from app.core.documento import format_documento_identidad

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

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
    email: Optional[str] = None
    nombre: str
    apellido: str
    nombre_completo: str
    rol_id: int
    rol: str
    departamento_id: int
    departamento: str
    requiere_password: bool
    debe_cambiar_password: bool = False

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse
    debe_cambiar_password: bool = False

class PrimerIngresoRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255, description="Correo electrónico institucional obligatorio")
    nuevo_password: str = Field(..., min_length=4, description="Nueva contraseña segura de acceso")
    confirmar_password: Optional[str] = Field(None, description="Confirmación de la nueva contraseña")

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v: Any) -> str:
        if not v or not str(v).strip():
            raise ValueError("El correo electrónico es requerido.")
        cleaned = str(v).strip().lower()
        if not EMAIL_REGEX.match(cleaned):
            raise ValueError("El formato del correo electrónico es inválido (ej: usuario@ula.ve).")
        return cleaned

    @model_validator(mode="after")
    def check_passwords_match(self) -> "PrimerIngresoRequest":
        if self.confirmar_password and self.nuevo_password != self.confirmar_password:
            raise ValueError("La confirmación de la contraseña no coincide con la nueva contraseña.")
        return self

class CambiarPasswordRequest(BaseModel):
    password_actual: str = Field(..., min_length=4, description="Contraseña actual")
    nuevo_password: str = Field(..., min_length=4, description="Nueva contraseña")
    confirmar_password: Optional[str] = Field(None, description="Confirmación de la nueva contraseña")

    @model_validator(mode="after")
    def check_passwords(self) -> "CambiarPasswordRequest":
        if self.password_actual == self.nuevo_password:
            raise ValueError("La nueva contraseña debe ser diferente a la contraseña actual.")
        if self.confirmar_password and self.nuevo_password != self.confirmar_password:
            raise ValueError("La confirmación de la contraseña no coincide.")
        return self

class AdminCambiarPasswordRequest(BaseModel):
    nuevo_password: str = Field(..., min_length=4, description="Nueva contraseña asignada al usuario")
    confirmar_password: Optional[str] = Field(None, description="Confirmación de la nueva contraseña")

    @model_validator(mode="after")
    def check_match(self) -> "AdminCambiarPasswordRequest":
        if self.confirmar_password and self.nuevo_password != self.confirmar_password:
            raise ValueError("La confirmación de la contraseña no coincide.")
        return self

class RecuperarPasswordSolicitud(BaseModel):
    identificador: str = Field(..., min_length=3, description="Cédula de identidad (ej: V-12345678) o correo electrónico registrado")

class VerificarTokenRequest(BaseModel):
    token: str = Field(..., min_length=1, description="Token o código de recuperación recibido por correo")

class RestablecerPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1, description="Token o código de recuperación recibido por correo")
    nuevo_password: str = Field(..., min_length=4, description="Nueva contraseña segura")
    confirmar_password: Optional[str] = Field(None, description="Confirmación de la nueva contraseña")

    @model_validator(mode="after")
    def check_match(self) -> "RestablecerPasswordRequest":
        if self.confirmar_password and self.nuevo_password != self.confirmar_password:
            raise ValueError("La confirmación de la contraseña no coincide con la nueva contraseña.")
        return self
