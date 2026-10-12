from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.core.network import validate_ip_or_cidr

class RedAutorizadaBase(BaseModel):
    direccion_ip: str = Field(..., description="Dirección IP (IPv4/IPv6) o rango en notación CIDR (ej: 192.168.1.0/24)")
    descripcion: str = Field(..., min_length=3, max_length=255, description="Punto físico o departamento de conexión")
    activo: bool = Field(True, description="Indica si la regla está vigente y habilitada")

    @field_validator("direccion_ip")
    @classmethod
    def check_valid_ip_or_cidr(cls, v: str) -> str:
        cleaned = v.strip()
        if not validate_ip_or_cidr(cleaned):
            raise ValueError(f"'{cleaned}' no es un formato de dirección IP o bloque CIDR válido (ej: 192.168.1.100 o 192.168.1.0/24).")
        return cleaned

class RedAutorizadaCreate(RedAutorizadaBase):
    pass

class RedAutorizadaUpdate(BaseModel):
    direccion_ip: Optional[str] = None
    descripcion: Optional[str] = Field(None, min_length=3, max_length=255)
    activo: Optional[bool] = None

    @field_validator("direccion_ip")
    @classmethod
    def check_valid_ip_or_cidr(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip()
            if not validate_ip_or_cidr(cleaned):
                raise ValueError(f"'{cleaned}' no es un formato de dirección IP o bloque CIDR válido.")
            return cleaned
        return v

class RedAutorizadaResponse(RedAutorizadaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int

class RedAutorizadaListResponse(BaseModel):
    items: List[RedAutorizadaResponse]
    total: int
    page: int
    limit: int
    total_pages: int
