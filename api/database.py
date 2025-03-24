import os
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

def get_db_engine():
    """Creates the SQLAlchemy engine only when called."""
    DATABASE_URL = os.getenv("DATABASE_URL")
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    return engine

def get_db():
    """Creates the SQLAlchemy session only when called."""
    engine = get_db_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
