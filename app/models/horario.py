import enum
from sqlalchemy import Column, Integer, SmallInteger, String, Enum, Time, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class TipoHorario(str, enum.Enum):
    FIJO = "fijo"
    FLEXIBLE = "flexible"

class HorarioPlantilla(Base):
    __tablename__ = "horarios_plantillas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False, unique=True)
    tipo = Column(
        Enum(TipoHorario, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    horas_requeridas = Column(Integer, nullable=True, default=0)

    detalles = relationship("HorarioDetalle", back_populates="plantilla", cascade="all, delete-orphan")
    usuarios = relationship("Usuario", back_populates="horario")

    def __repr__(self):
        return f"<HorarioPlantilla(id={self.id}, nombre='{self.nombre}', tipo='{self.tipo}')>"

class HorarioDetalle(Base):
    __tablename__ = "horarios_detalles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    horario_plantilla_id = Column(Integer, ForeignKey("horarios_plantillas.id", ondelete="CASCADE"), nullable=False)
    dia_semana = Column(SmallInteger, nullable=False)  # 1=Lunes, 2=Martes, ..., 7=Domingo
    hora_entrada = Column(Time, nullable=False)
    hora_salida = Column(Time, nullable=False)

    plantilla = relationship("HorarioPlantilla", back_populates="detalles")

    def __repr__(self):
        return f"<HorarioDetalle(id={self.id}, plantilla_id={self.horario_plantilla_id}, dia={self.dia_semana}, entrada={self.hora_entrada}, salida={self.hora_salida})>"
