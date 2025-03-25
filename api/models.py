from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Float
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import datetime

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class Business(Base):
    __tablename__ = "businesses"
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(String(255), unique=True, nullable=False)
    industry = Column(String(255))
    address = Column(String(255))
    address2 = Column(String(255))
    city = Column(String(255))
    state = Column(String(255))
    zip = Column(String(20))
    phone = Column(String(20))
    website = Column(String(255))
    email = Column(String(255))
    notes = Column(String)
    sources = relationship("Source", secondary="business_sources", back_populates="businesses")
    contacts = relationship("Contact", secondary="business_contacts", back_populates="businesses")

class Contact(Base):
    __tablename__ = "contacts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True)
    phone = Column(String(20))
    title = Column(String(255))
    notes = Column(String)
    businesses = relationship("Business", secondary="business_contacts", back_populates="contacts")
    sources = relationship("Source", secondary="source_contacts", back_populates="contacts")

class BusinessContact(Base):
    __tablename__ = "business_contacts"
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), primary_key=True)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"), primary_key=True)

class Source(Base):
    __tablename__ = "sources"
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(String(255), unique=True, nullable=False)
    url = Column(String(255), unique=True, nullable=True)
    notes = Column(String)
    businesses = relationship("Business", secondary="business_sources", back_populates="sources")
    contacts = relationship("Contact", secondary="source_contacts", back_populates="sources")

class BusinessSource(Base):
    __tablename__ = "business_sources"
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), primary_key=True)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), primary_key=True)
    
class SourceContact(Base):
    __tablename__ = "source_contacts"
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), primary_key=True)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"), primary_key=True)

class CoverageZipList(Base):
    __tablename__ = "coverage_zip_list"
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    params = Column(String, unique=True, nullable=False)
    zips = Column(String, nullable=False)

class ZipCode(Base):
    __tablename__ = "zip_codes"
    zip = Column(String, primary_key=True, unique=True, nullable=False)
    plus4 = Column(Boolean, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    county = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    timezone = Column(String, nullable=True)

class WebSearchCache(Base):
    __tablename__ = "web_search_results"
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    query = Column(String, nullable=False)
    results = Column(String, nullable=False)
    datetime = Column(DateTime, default=datetime.datetime.now)