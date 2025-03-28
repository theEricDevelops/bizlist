from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models import Base, generate_uuid

class Source(Base):
    __tablename__ = "sources"
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(String(255), unique=True, nullable=False)
    url = Column(String(255), unique=True, nullable=True)
    notes = Column(String)
    businesses = relationship("Business", secondary="business_sources", back_populates="sources")
    contacts = relationship("Contact", secondary="source_contacts", back_populates="sources")