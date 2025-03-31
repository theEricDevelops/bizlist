# api/routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List
import logging

from app.core.database import get_db
from app.schemas.contact import BusinessSchema, ContactSchema, SourceSchema
from app.schemas.location import LocationSchema, CoverageZipListSchema
from app.models.contact import Business, Contact
from app.models.source import Source
from app.models.location import CoverageZipList
from app.models.email import EmailMessage
from app.services.gmail import GmailService
from app.services.business import BusinessService
from app.services.scrapers.gaf import GAFScraper

mail = GmailService()
business_service = BusinessService()

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/")
async def root():
    return {"message": "Welcome to the BizList API!"}

@router.post("/contact/", response_model=ContactSchema)
def create_contact(contact: ContactSchema, db: Session = Depends(get_db)):
    """Create a new contact."""
    try:
        db_contact = Contact(**contact.model_dump(exclude={"id", "businesses", "sources"}))
        db.add(db_contact)
        db.commit()
        db.refresh(db_contact)
        return db_contact
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating contact: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@router.get("/contacts/", response_model=List[ContactSchema])
def read_contacts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Read all contacts."""
    try:
        contacts = db.query(Contact).offset(skip).limit(limit).all()
        return contacts
    except SQLAlchemyError as e:
        logger.error(f"Error reading contacts: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@router.get("/contact/{contact_id}", response_model=ContactSchema)
def read_contact(contact_id: int, db: Session = Depends(get_db)):
    """Read a specific contact by ID."""
    try:
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if contact is None:
            raise HTTPException(status_code=404, detail="Contact not found")
        return contact
    except SQLAlchemyError as e:
        logger.error(f"Error reading contact: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@router.post("/source/", response_model=SourceSchema)
def create_source(source: SourceSchema, db: Session = Depends(get_db)):
    """Create a new source."""
    try:
        db_source = Source(**source.model_dump(exclude={"id", "businesses", "contacts"}))
        db.add(db_source)
        db.commit()
        db.refresh(db_source)
        return db_source
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating source: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@router.get("/sources/", response_model=List[SourceSchema])
def read_sources(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Read all sources."""
    try:
        sources = db.query(Source).offset(skip).limit(limit).all()
        return sources
    except SQLAlchemyError as e:
        logger.error(f"Error reading sources: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@router.get("/source/{source_id}", response_model=SourceSchema)
def read_source(source_id: int, db: Session = Depends(get_db)):
    """Read a specific source by ID."""
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if source is None:
            raise HTTPException(status_code=404, detail="Source not found")
        return source
    except SQLAlchemyError as e:
        logger.error(f"Error reading source: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@router.post("/scrape/gaf", response_model=List[BusinessSchema])
def extract_gaf(location: LocationSchema, radius: int = 25, max_pages: int = -1, db: Session = Depends(get_db)):
    """Extract data from GAF based on location and radius."""
    gaf = GAFScraper()
    try:
        logger.info(f"Extracting GAF data for location: {location.model_dump()}, radius: {radius}, max_pages: {max_pages}")
        data = gaf._get_all_listings(db, location.model_dump(), radius, max_pages)
        businesses = []
        
        for business in data:
            result = business_service.add(db, business)
            if result and "business" in result:
                businesses.append(result["business"])
        return businesses
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error extracting GAF data: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logger.error(f"Error extracting GAF data: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@router.post("/internal/llm/extract-html")
def send_to_llm(html: str, expected: List[str] = []):
    """Send HTML to LLM for contact info extraction."""
    try:
        logger.info(f"Sending HTML to LLM for contact info extraction.")
        
        result = {"status": "Need to do this"}
        return result
    except Exception as e:
        logger.error(f"Error sending to LLM: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@router.post("/internal/zip/list/", response_model=CoverageZipListSchema)
def create_coverage_zip_list(coverage_zip_list: CoverageZipListSchema, db: Session = Depends(get_db)):
    """Create a new coverage zip list."""
    try:
        db_coverage_zip_list = CoverageZipList(**coverage_zip_list.model_dump())
        db.add(db_coverage_zip_list)
        db.commit()
        db.refresh(db_coverage_zip_list)
        return db_coverage_zip_list
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating coverage zip list: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logger.error(f"Error creating coverage zip list: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@router.get("/internal/zip/lists/", response_model=List[CoverageZipListSchema])
def read_coverage_zip_lists(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Returns a list of coverage zip lists."""
    try:
        coverage_zip_lists = db.query(CoverageZipList).offset(skip).limit(limit).all()
        return coverage_zip_lists
    except SQLAlchemyError as e:
        logger.error(f"Error reading coverage zip lists: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logger.error(f"Error reading coverage zip lists: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@router.get("/internal/zip/list/{coverage_zip_list_id}", response_model=CoverageZipListSchema)
def read_coverage_zip_list(coverage_zip_list_id: int, db: Session = Depends(get_db)):
    """Read a specific coverage zip list by ID."""
    try:
        coverage_zip_list = db.query(CoverageZipList).filter(CoverageZipList.id == coverage_zip_list_id).first()
        if coverage_zip_list is None:
            raise HTTPException(status_code=404, detail="Coverage zip list not found")
        return coverage_zip_list
    except SQLAlchemyError as e:
        logger.error(f"Error reading coverage zip list: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logger.error(f"Error reading coverage zip list: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    
@router.get("/internal/zip/location/{zip}",)
def read_zip_location(zip: str, db: Session = Depends(get_db)):
    """Read the location of a specific zip code."""
    try:
        coverage_zip_list = db.query(CoverageZipList).filter(CoverageZipList.zip == zip).first()
        if coverage_zip_list is None:
            raise HTTPException(status_code=404, detail="Zip code not found")
        return coverage_zip_list
    except SQLAlchemyError as e:
        logger.error(f"Error reading zip code location: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logger.error(f"Error reading zip code location: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    
@router.post("/internal/email/send", response_model=EmailMessage)
def send_mail(email: str, subject: str, body: str):
    """Send an email to the specified address."""
    try:
        message = mail.draft(email, subject, body)
        result = mail.send(message)
        return result
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")