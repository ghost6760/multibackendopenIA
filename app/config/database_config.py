# app/config/database_config.py
import os
from typing import Dict, Any

class DatabaseConfig:
    """Configuración de PostgreSQL"""
    
    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = int(os.getenv('DB_PORT', 5432))
        self.name = os.getenv('DB_NAME', 'prompts_db')
        self.user = os.getenv('DB_USER', 'postgres')
        self.password = os.getenv('DB_PASSWORD', 'password')
        self.url = os.getenv('DATABASE_URL')
        
        # Pool settings
        self.min_connections = int(os.getenv('DB_MIN_CONN', 2))
        self.max_connections = int(os.getenv('DB_MAX_CONN', 10))
        
    @property
    def connection_string(self) -> str:
        """Obtener string de conexión"""
        if self.url:
            return self.url
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para logs"""
        return {
            "host": self.host,
            "port": self.port,
            "database": self.name,
            "user": self.user,
            "min_connections": self.min_connections,
            "max_connections": self.max_connections
        }

def get_database_config() -> DatabaseConfig:
    """Obtener configuración de base de datos"""
    return DatabaseConfig()
