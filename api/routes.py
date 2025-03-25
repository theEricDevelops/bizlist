# api/routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List
import logging

from api.database import get_db
from api.dependencies import get_db_conn
from api.schemas import BusinessSchema, ContactSchema, SourceSchema, LocationSchema, CoverageZipListSchema
from api.services import extract_gaf_data, insert_company_data, send_company_to_llm_for_contact_info, export_to_csv
from api.models import Business, Contact, Source, CoverageZipList

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/")
async def root():
    return {"message": "Welcome to the BizList API!"}

@router.post("/business/", response_model=BusinessSchema)
def create_business(business: BusinessSchema, db: Session = Depends(get_db)):
    """Create a new business."""
    try:
        db_business = Business(**business.model_dump(exclude={"id", "sources", "contacts"}))
        db.add(db_business)
        db.commit()
        db.refresh(db_business)
        return db_business
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating business: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@router.get("/businesses/", response_model=List[BusinessSchema])
def read_businesses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Read all businesses."""
    try:
        businesses = db.query(Business).offset(skip).limit(limit).all()
        return businesses
    except SQLAlchemyError as e:
        logger.error(f"Error reading businesses: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    
@router.get("/businesses/export", response_model=List[BusinessSchema])
def read_businesses_export(db: Session = Depends(get_db)):
    """Read all businesses for export."""
    try:
        businesses = db.query(Business).all()
        response = export_to_csv(businesses)
        return response
    except SQLAlchemyError as e:
        logger.error(f"Error reading businesses for export: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@router.get("/business/{business_id}", response_model=BusinessSchema)
def read_business(business_id: int, db: Session = Depends(get_db)):
    """Read a specific business by ID."""
    try:
        business = db.query(Business).filter(Business.id == business_id).first()
        if business is None:
            raise HTTPException(status_code=404, detail="Business not found")
        return business
    except SQLAlchemyError as e:
        logger.error(f"Error reading business: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

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
def extract_gaf(location: LocationSchema, radius: int = 25, max_pages: int = -1, db: Session = Depends(get_db_conn)):
    """Extract data from GAF based on location and radius."""
    try:
        logger.info(f"Extracting GAF data for location: {location.model_dump()}, radius: {radius}, max_pages: {max_pages}")
        source_data = extract_gaf_data(db, location.model_dump(), radius, max_pages)
        businesses = []
        for company in source_data:
            result = insert_company_data(db, company)
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
        result = send_company_to_llm_for_contact_info(html, expected)
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
