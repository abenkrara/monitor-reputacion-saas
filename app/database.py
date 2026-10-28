"""
Gestión de conexión a base de datos y sesiones con SQLAlchemy.
Utiliza SQLite por defecto para facilitar portabilidad y despliegue local.
"""

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import get_settings

settings = get_settings()

# Asegurar que el directorio data/ exista si se usa SQLite local
if settings.DATABASE_URL.startswith("sqlite"):
    db_path_str = settings.DATABASE_URL.replace("sqlite:///", "")
    db_path = Path(db_path_str).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

# Configurar motor de base de datos
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Generador de sesión de base de datos para inyección de dependencias en FastAPI."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Crea todas las tablas definidas en los modelos si no existen."""
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

