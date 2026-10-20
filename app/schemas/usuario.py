from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator
from app.core.documento import format_documento_identidad

class UsuarioBase(BaseModel):
    documento_identidad: str = Field(..., description="Cédula de identidad (ej: v-12345678)")
    nombre: str = Field(..., min_length=2, max_length=100, description="Nombres del usuario")
    apellido: str = Field(..., min_length=2, max_length=100, description="Apellidos del usuario")
    rol_id: int = Field(..., description="ID del rol asignado")
    departamento_id: int = Field(..., description="ID de la unidad organizacional asignada")
    horario_id: Optional[int] = Field(None, description="ID de la plantilla de horario asignada")
    activo: bool = Field(True, description="Estado de activación del usuario")

    @field_validator("documento_identidad", mode="before")
    @classmethod
    def validate_and_format_documento(cls, v: Any) -> str:
        if v is None:
            raise ValueError("El documento de identidad es requerido.")
        return format_documento_identidad(str(v))

    @model_validator(mode="before")
    @classmethod
    def handle_aliases_and_types(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Mapear nombres/apellidos a singular si viene plural
            if "nombre" not in data and "nombres" in data:
                data["nombre"] = data["nombres"]
            if "apellido" not in data and "apellidos" in data:
                data["apellido"] = data["apellidos"]
            # Convertir vacíos a None en horario_id
            if "horario_id" in data and (data["horario_id"] == "" or data["horario_id"] is None):
                data["horario_id"] = None
        return data

class UsuarioCreate(UsuarioBase):
    password: Optional[str] = Field(None, min_length=4, description="Contraseña requerida si el rol tiene privilegios administrativos")

class UsuarioUpdate(BaseModel):
    documento_identidad: Optional[str] = None
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    apellido: Optional[str] = Field(None, min_length=2, max_length=100)
    rol_id: Optional[int] = None
    departamento_id: Optional[int] = None
    horario_id: Optional[int] = None
    activo: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=4)

    @field_validator("documento_identidad", mode="before")
    @classmethod
    def validate_and_format_documento(cls, v: Any) -> Optional[str]:
        if v is None or v == "":
            return None
        return format_documento_identidad(str(v))

    @model_validator(mode="before")
    @classmethod
    def handle_aliases_and_types(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "nombre" not in data and "nombres" in data:
                data["nombre"] = data["nombres"]
            if "apellido" not in data and "apellidos" in data:
                data["apellido"] = data["apellidos"]
            if "horario_id" in data and (data["horario_id"] == "" or data["horario_id"] is None):
                data["horario_id"] = None
        return data

class UsuarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    documento_identidad: str
    nombre: str
    apellido: str
    nombre_completo: str
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    rol_id: int
    rol: str
    rol_nombre: Optional[str] = None
    departamento_id: int
    departamento: str
    departamento_nombre: Optional[str] = None
    horario_id: Optional[int] = None
    horario: Optional[str] = None
    horario_nombre: Optional[str] = None
    tiene_biometria: bool = False
    codigo_qr: Optional[str] = None
    tiene_password: bool = False
    activo: bool = True

    @model_validator(mode="after")
    def sync_aliases(self) -> "UsuarioResponse":
        if not self.nombres:
            self.nombres = self.nombre
        if not self.apellidos:
            self.apellidos = self.apellido
        if not self.rol_nombre:
            self.rol_nombre = self.rol
        if not self.departamento_nombre:
            self.departamento_nombre = self.departamento
        if not self.horario_nombre:
            self.horario_nombre = self.horario
        return self

class UsuarioListResponse(BaseModel):
    items: List[UsuarioResponse]
    total: int
    page: int
    limit: int
    total_pages: int

class CheckDocumentoResponse(BaseModel):
    disponible: bool
    documento_identidad: str
    mensaje: str

class BiometriaEnrollRequest(BaseModel):
    vector: List[float] = Field(..., min_length=128, max_length=128, description="Vector de 128 descriptores faciales extraídos por face-api.js")

    @model_validator(mode="before")
    @classmethod
    def handle_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "vector" not in data and "descriptor_facial" in data:
                data["vector"] = data["descriptor_facial"]
        return data
