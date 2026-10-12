import enum
from sqlalchemy import Column, Integer, String, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base

class TipoDepartamento(str, enum.Enum):
    DIRECCION = "dirección"
    COORDINACION = "coordinación"
    SECCION = "sección"
    OFICINA = "oficina"

class Departamento(Base):
    __tablename__ = "departamentos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False, unique=True)
    tipo = Column(
        Enum(TipoDepartamento, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    usuarios = relationship("Usuario", back_populates="departamento")

    def __repr__(self):
        return f"<Departamento(id={self.id}, nombre='{self.nombre}', tipo='{self.tipo}')>"
