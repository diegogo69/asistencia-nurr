from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator
from app.models.asistencia import MetodoValidacion, EstadoCumplimiento

class MarcacionRequest(BaseModel):
    documento_identidad: str = Field(..., description="Documento de identidad del usuario")
    metodo: MetodoValidacion = Field(MetodoValidacion.FACIAL, description="Método de validación: facial o qr")
    vector_facial: Optional[List[float]] = Field(None, description="Vector de 128 floats capturado por face-api.js")
    codigo_qr: Optional[str] = Field(None, description="Hash/token de la credencial QR escaneada")

    @model_validator(mode="before")
    @classmethod
    def handle_aliases_and_methods(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "vector_facial" not in data and "descriptor_facial" in data:
                data["vector_facial"] = data["descriptor_facial"]
            if "codigo_qr" not in data and "qr_hash" in data:
                data["codigo_qr"] = data["qr_hash"]
            if "metodo" not in data:
                if data.get("codigo_qr"):
                    data["metodo"] = MetodoValidacion.QR
                else:
                    data["metodo"] = MetodoValidacion.FACIAL
        return data

class MarcacionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asistencia_id: int
    usuario_id: int
    documento_identidad: str
    nombre_completo: str
    departamento: str
    tipo_evento: str  # ENTRADA o SALIDA
    fecha: str
    hora: str
    estado_cumplimiento: str
    metodo_validacion: str
    mensaje: str

    tipo_marcacion: Optional[str] = None
    usuario_nombre: Optional[str] = None
    departamento_nombre: Optional[str] = None
    hora_registrada: Optional[str] = None
    estado: Optional[str] = None
    metodo: Optional[str] = None

    @model_validator(mode="after")
    def sync_aliases(self) -> "MarcacionResponse":
        if not self.tipo_marcacion:
            self.tipo_marcacion = self.tipo_evento
        if not self.usuario_nombre:
            self.usuario_nombre = self.nombre_completo
        if not self.departamento_nombre:
            self.departamento_nombre = self.departamento
        if not self.hora_registrada:
            self.hora_registrada = self.hora
        if not self.estado:
            self.estado = self.estado_cumplimiento
        if not self.metodo:
            self.metodo = self.metodo_validacion
        return self

class VerificarUsuarioMarcacionResponse(BaseModel):
    registrado: bool
    activo: bool
    documento_identidad: str = ""
    usuario_id: Optional[int] = None
    nombre_completo: str = ""
    departamento: str = ""
    tiene_biometria: bool = False
    mensaje: str = ""
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    horario: Optional[str] = None
    accion_esperada: Optional[str] = "ENTRADA"

    @model_validator(mode="after")
    def sync_aliases(self) -> "VerificarUsuarioMarcacionResponse":
        if not self.nombres:
            parts = self.nombre_completo.split(" ", 1)
            self.nombres = parts[0] if parts else ""
            self.apellidos = parts[1] if len(parts) > 1 else ""
        return self
