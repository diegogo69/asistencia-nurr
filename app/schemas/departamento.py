from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.models.departamento import TipoDepartamento

class DepartamentoBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100, description="Nombre de la unidad organizacional")
    tipo: TipoDepartamento = Field(..., description="Tipo de unidad jerárquica (dirección, coordinación, sección, oficina)")

class DepartamentoCreate(DepartamentoBase):
    pass

class DepartamentoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    tipo: Optional[TipoDepartamento] = None

class DepartamentoResponse(DepartamentoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    total_usuarios: int = 0

class DepartamentoListResponse(BaseModel):
    items: List[DepartamentoResponse]
    total: int
    page: int
    limit: int
    total_pages: int
