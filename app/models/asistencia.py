import enum
from sqlalchemy import Column, Integer, String, Date, Time, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class EstadoCumplimiento(str, enum.Enum):
    PUNTUAL = "puntual"
    RETRASO = "retraso"
    ANTICIPADA = "anticipada"
    INCOMPLETO = "incompleto"
    PENDIENTE = "pendiente"

class MetodoValidacion(str, enum.Enum):
    FACIAL = "facial"
    QR = "qr"

class Asistencia(Base):
    __tablename__ = "asistencias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    hora_entrada = Column(Time, nullable=False)
    hora_salida = Column(Time, nullable=True)
    estado_cumplimiento = Column(
        Enum(EstadoCumplimiento, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=EstadoCumplimiento.PENDIENTE
    )
    ip_registro_entrada = Column(String(45), nullable=False)
    ip_registro_salida = Column(String(45), nullable=True)
    metodo_validacion = Column(
        Enum(MetodoValidacion, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    usuario = relationship("Usuario", back_populates="asistencias")
    resoluciones = relationship("AsistenciaPendiente", back_populates="asistencia", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Asistencia(id={self.id}, usuario_id={self.usuario_id}, fecha={self.fecha}, entrada={self.hora_entrada}, estado='{self.estado_cumplimiento}')>"
