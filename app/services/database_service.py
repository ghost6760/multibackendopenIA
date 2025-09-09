# app/services/database_service.py
import os
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
import logging

logger = logging.getLogger(__name__)

class DatabaseService:
    """Servicio de conexión a PostgreSQL"""
    
    def __init__(self):
        self.pool = None
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Inicializar pool de conexiones"""
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            database_url = (
                f"postgresql://{os.getenv('DB_USER', 'postgres')}:"
                f"{os.getenv('DB_PASSWORD', 'password')}@"
                f"{os.getenv('DB_HOST', 'localhost')}:"
                f"{os.getenv('DB_PORT', '5432')}/"
                f"{os.getenv('DB_NAME', 'prompts_db')}"
            )
        
        self.pool = ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            dsn=database_url
        )
        logger.info("PostgreSQL connection pool initialized")

# Instancia global
_db_service = None

def get_database_service():
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service
