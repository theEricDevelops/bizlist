# /app/models/source.py

from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models import Base, generate_uuid

class Source(Base):
    __tablename__ = "sources"
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(String(255), unique=True, nullable=False)
    url = Column(String(255), unique=True, nullable=True)
    notes = Column(String, nullable=True)

    businesses = relationship("BusinessSource", back_populates="source")
    contacts = relationship("SourceContact", back_populates="source")