from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Business(Base):
    __tablename__ = "businesses"
    id = Column(Integer, primary_key=True)
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
    id = Column(Integer, primary_key=True)
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
    business_id = Column(Integer, ForeignKey("businesses.id"), primary_key=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), primary_key=True)

class Source(Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    url = Column(String(255), unique=True, nullable=True)
    notes = Column(String)
    businesses = relationship("Business", secondary="business_sources", back_populates="sources")
    contacts = relationship("Contact", secondary="source_contacts", back_populates="sources")

class BusinessSource(Base):
    __tablename__ = "business_sources"
    business_id = Column(Integer, ForeignKey("businesses.id"), primary_key=True)
    source_id = Column(Integer, ForeignKey("sources.id"), primary_key=True)
    
class SourceContact(Base):
    __tablename__ = "source_contacts"
    source_id = Column(Integer, ForeignKey("sources.id"), primary_key=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), primary_key=True)

class CoverageZipList(Base):
    __tablename__ = "coverage_zip_list"
    id = Column(Integer, primary_key=True)
    params = Column(String, unique=True, nullable=False)
    zips = Column(String, nullable=False)
