from typing import Optional, List
from datetime import time
from pydantic import BaseModel, Field, ConfigDict
from app.models.asistencia import EstadoCumplimiento

class AsistenciaIncompletaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    documento_identidad: str
    nombre_completo: str
    departamento: str
    fecha: str
    hora_entrada: str
    hora_salida: Optional[str] = None
    estado_cumplimiento: str
    ip_registro_entrada: str

class ListIncompletasResponse(BaseModel):
    items: List[AsistenciaIncompletaResponse]
    total: int
    page: int
    limit: int
    total_pages: int

class ResolverIncidenciaRequest(BaseModel):
    asistencia_id: int = Field(..., description="ID del registro de asistencia a corregir")
    hora_salida: time = Field(..., description="Hora de salida acordada o constatada")
    nuevo_estado: EstadoCumplimiento = Field(..., description="Nuevo estado de cumplimiento asignado tras la evaluación")
    observacion: str = Field(..., min_length=10, description="Justificación explicativa obligatoria del cambio")

class AsistenciaPendienteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asistencia_id: int
    coordinador_id: int
    coordinador_nombre: str
    usuario_afectado: str
    fecha_resolucion: str
    estado_anterior: str
    estado_nuevo: str
    observacion: str

class ListResolucionesResponse(BaseModel):
    items: List[AsistenciaPendienteResponse]
    total: int
    page: int
    limit: int
    total_pages: int
