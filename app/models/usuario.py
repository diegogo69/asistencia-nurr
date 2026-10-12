from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    horario_id = Column(Integer, ForeignKey("horarios_plantillas.id"), nullable=True)
    rol_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    departamento_id = Column(Integer, ForeignKey("departamentos.id"), nullable=False)
    documento_identidad = Column(String(20), unique=True, nullable=False, index=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    vector_biometrico = Column(Text, nullable=True)  # Vector 128D serializado en JSON (face-api.js)
    codigo_qr = Column(String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)
    activo = Column(Boolean, default=True, nullable=False)

    departamento = relationship("Departamento", back_populates="usuarios")
    rol = relationship("Rol", back_populates="usuarios")
    horario = relationship("HorarioPlantilla", back_populates="usuarios")
    asistencias = relationship("Asistencia", back_populates="usuario")

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}"

    def __repr__(self):
        return f"<Usuario(id={self.id}, doc='{self.documento_identidad}', nombre='{self.nombre_completo}', rol_id={self.rol_id})>"
