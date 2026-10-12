import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Asistencia-NURR"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Seguridad y JWT
    SECRET_KEY: str = "ula-nurr-super-secret-key-change-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 horas
    
    # Base de Datos (SQLite por defecto para desarrollo, MySQL para producción)
    DATABASE_URL: str = "sqlite:///./asistencia_nurr.db"
    
    # Rutas SSL
    SSL_CERT_FILE: str = "certs/cert.pem"
    SSL_KEY_FILE: str = "certs/key.pem"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # Margen de tolerancia horaria en minutos
    TOLERANCIA_MINUTOS_ENTRADA: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
