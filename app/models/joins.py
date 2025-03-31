# /app/models/joins.py

from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models import Base, generate_uuid

class BusinessSource(Base):
    __tablename__ = "business_sources"
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)

    business = relationship("Business", back_populates="sources")
    source = relationship("Source", back_populates="businesses")
    
class SourceContact(Base):
    __tablename__ = "source_contacts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False)

    source = relationship("Source", back_populates="contacts")
    contact = relationship("Contact", back_populates="sources")

class BusinessContact(Base):
    __tablename__ = "business_contacts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    business_id =Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False)

    business = relationship("Business", back_populates="contacts")
    contact = relationship("Contact", back_populates="businesses")


