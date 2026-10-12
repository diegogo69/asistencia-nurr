from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class HistorialItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    documento_identidad: str
    nombre_completo: str
    departamento: str
    rol: str
    fecha: str
    hora_entrada: str
    hora_salida: Optional[str] = None
    horas_trabajadas: float = 0.0
    estado_cumplimiento: str
    metodo_validacion: str
    fue_corregido: bool = False

class HistorialListResponse(BaseModel):
    items: List[HistorialItemResponse]
    total: int
    page: int
    limit: int
    total_pages: int

class UsuarioReporteMetricas(BaseModel):
    usuario_id: int
    documento_identidad: str
    nombre_completo: str
    rol: str
    departamento: str
    total_dias_asistidos: int
    horas_totales_acumuladas: float
    puntuales: int
    retrasos: int
    anticipadas: int
    incompletos: int

class ReporteResumenResponse(BaseModel):
    rango_desde: Optional[str] = None
    rango_hasta: Optional[str] = None
    total_marcaciones: int
    total_horas_acumuladas: float
    total_puntuales: int
    total_retrasos: int
    total_anticipadas: int
    total_incompletos: int
    usuarios: List[UsuarioReporteMetricas]
