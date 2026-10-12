from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class AsistenciaPendiente(Base):
    __tablename__ = "asistencias_pendientes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asistencia_id = Column(Integer, ForeignKey("asistencias.id", ondelete="CASCADE"), nullable=False)
    coordinador_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    observacion = Column(Text, nullable=False)
    fecha_resolucion = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    estado_anterior = Column(String(20), nullable=False)
    estado_nuevo = Column(String(20), nullable=False)

    asistencia = relationship("Asistencia", back_populates="resoluciones")
    coordinador = relationship("Usuario")

    def __repr__(self):
        return f"<AsistenciaPendiente(id={self.id}, asistencia_id={self.asistencia_id}, coordinador_id={self.coordinador_id}, nuevo_estado='{self.estado_nuevo}')>"
