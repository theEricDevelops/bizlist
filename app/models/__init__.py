from sqlalchemy.orm import declarative_base
from uuid import uuid4

Base = declarative_base()

def generate_uuid():
    return str(uuid4())

# Import all the models here to ensure they are registered with SQLAlchemy
from .contact import Business, Contact
from .source import Source
from .location import ZipCode, CoverageZipList
from .email import EmailMessage
from .cache import WebSearchCache
from .joins import BusinessSource, SourceContact, BusinessContact