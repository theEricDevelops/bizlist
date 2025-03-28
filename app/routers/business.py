from fastapi import APIRouter
from fastapi import Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db

from app.services.logger import Logger
from app.services.exporter import Exporter

from app.models.contact import Business
from app.schemas.contact import BusinessSchema

log = Logger('router-business')

business_router = APIRouter()

@business_router.post("/", response_model=BusinessSchema)
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
        log.error(f"Error creating business: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@business_router.get("", response_model=List[BusinessSchema])
def read_businesses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Read all businesses."""
    try:
        businesses = db.query(Business).offset(skip).limit(limit).all()
        return businesses
    except SQLAlchemyError as e:
        log.error(f"Error reading businesses: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    
@business_router.get("/businesses/export", response_model=List[BusinessSchema])
def read_businesses_export(db: Session = Depends(get_db)):
    """Read all businesses for export."""
    export = Exporter()
    try:
        businesses = db.query(Business).all()
        response = export.to_csv(businesses)
        return response
    except SQLAlchemyError as e:
        log.error(f"Error reading businesses for export: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@business_router.get("/business/{business_id}", response_model=BusinessSchema)
def read_business(business_id: int, db: Session = Depends(get_db)):
    """Read a specific business by ID."""
    try:
        business = db.query(Business).filter(Business.id == business_id).first()
        if business is None:
            raise HTTPException(status_code=404, detail="Business not found")
        return business
    except SQLAlchemyError as e:
        log.error(f"Error reading business: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")