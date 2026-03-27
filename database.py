from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Crea un archivo local llamado tienda.db
SQLALCHEMY_DATABASE_URL = "sqlite:///./tienda.db"

# connect_args solo es necesario para SQLite en FastAPI
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependencia para inyectar la sesión en las rutas
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()