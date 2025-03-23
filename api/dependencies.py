from .database import get_db

def get_db_conn():
    """Get a database connection."""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()
