from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# Ensure DATABASE_URL is set
if not settings.DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in .env file")

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True, 
    pool_recycle=3600
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
