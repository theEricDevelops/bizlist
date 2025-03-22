import os
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.declarative import declarative_base

# Database connection string (from your .env file)
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Base = declarative_base()

class Business(Base):
    __tablename__ = "businesses"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    industry = Column(String)
    location = Column(String)
    contacts = relationship("Contact", secondary="business_contacts", back_populates="businesses")

class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True)
    phone = Column(String)
    title = Column(String)
    businesses = relationship("Business", secondary="business_contacts", back_populates="contacts")

class BusinessContact(Base):
    __tablename__ = "business_contacts"
    business_id = Column(Integer, ForeignKey("businesses.id"), primary_key=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), primary_key=True)

class Source(Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    url = Column(String, unique=True, nullable=True)

Base.metadata.create_all(engine) # Create tables if they don't exist

