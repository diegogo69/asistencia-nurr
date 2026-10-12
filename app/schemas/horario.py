from typing import Optional, List
from datetime import time
from pydantic import BaseModel, Field, model_validator, ConfigDict
from app.models.horario import TipoHorario

class HorarioDetalleItem(BaseModel):
    dia_semana: int = Field(..., ge=1, le=7, description="Día de la semana (1=Lunes ... 7=Domingo)")
    hora_entrada: time = Field(..., description="Hora de entrada requerida")
    hora_salida: time = Field(..., description="Hora de salida requerida")

    @model_validator(mode="after")
    def validate_block_times(self):
        if self.hora_entrada >= self.hora_salida:
            raise ValueError(f"En el día {self.dia_semana}, la hora de entrada ({self.hora_entrada}) debe ser anterior a la hora de salida ({self.hora_salida}).")
        return self

class HorarioDetalleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dia_semana: int
    hora_entrada: time
    hora_salida: time

class HorarioPlantillaCreate(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=100, description="Nombre de la plantilla de horario")
    tipo: TipoHorario = Field(..., description="Tipo de horario: fijo o flexible")
    horas_requeridas: Optional[int] = Field(0, ge=0, description="Cantidad mínima de horas semanales (para horarios flexibles de pasantes)")
    detalles: Optional[List[HorarioDetalleItem]] = Field([], description="Bloques diarios detallados (requerido para horarios fijos)")

class HorarioPlantillaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=3, max_length=100)
    tipo: Optional[TipoHorario] = None
    horas_requeridas: Optional[int] = Field(None, ge=0)
    detalles: Optional[List[HorarioDetalleItem]] = None

class HorarioPlantillaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    tipo: TipoHorario
    horas_requeridas: int
    detalles: List[HorarioDetalleResponse] = []
    total_usuarios: int = 0

class HorarioPlantillaListResponse(BaseModel):
    items: List[HorarioPlantillaResponse]
    total: int
    page: int
    limit: int
    total_pages: int
