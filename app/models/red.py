from sqlalchemy import Column, Integer, String, Boolean
from app.core.database import Base

class RedAutorizada(Base):
    __tablename__ = "redes_autorizadas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    direccion_ip = Column(String(45), nullable=False, unique=True)
    descripcion = Column(String(255), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<RedAutorizada(id={self.id}, ip='{self.direccion_ip}', activo={self.activo})>"
