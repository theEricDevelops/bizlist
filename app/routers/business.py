from urllib.parse import unquote_plus

from fastapi import APIRouter
from fastapi import Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db

from app.services.logger import Logger
from app.services.exporter import Exporter

from app.models.contact import Business
from app.schemas.contact import BusinessSchema, BusinessSchemaRef

log = Logger('router-business', log_level='DEBUG')

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

@business_router.get("/", response_model=List[BusinessSchemaRef])
def read_businesses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Read all businesses."""
    try:
        businesses = db.query(Business).offset(skip).limit(limit).all()

        data = []
        for business in businesses:
            business_dict = business.__dict__.copy()
            for key in business_dict:
                if business_dict[key] == '':
                    business_dict[key] = None
            if business_dict['notes'] is not List:
                print(f"Business {business.id} notes is not a list, converting to list")
                business_dict['notes'] = [business_dict['notes']]
            data.append(business_dict)

        return [BusinessSchemaRef.model_validate(business) for business in data]
    except SQLAlchemyError as e:
        log.error(f"Error reading businesses: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    
@business_router.get("/export", response_model=str)
def read_businesses_export(db: Session = Depends(get_db)):
    """Read all businesses for export."""
    export = Exporter()
    try:
        businesses = db.query(Business).all()
        log.info(f"Exporting {len(businesses)} businesses to CSV")
        response = export.to_csv(businesses)
        return response
    except SQLAlchemyError as e:
        log.error(f"Error reading businesses for export: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    
@business_router.get("/export/{params}", response_model=str)
def export_businesses(params: str, db: Session = Depends(get_db)):
    """Export a business by name into CSV with optional filters."""
    export = Exporter()
    try:
        log.info(f"Export request with path parameter: {params}")
        
        # Check if the name contains query parameters
        query_params = {}
        filename = None
        fieldnames = None
        original_params = params  # Store original params before splitting
        
        if '=' in params:
            # Parse query parameters from name
            param_items = params.split('&')
            for param in param_items:
                if '=' in param:
                    key, value = param.split('=', 1)
                    value = unquote_plus(value)
                    if key == 'filename':
                        filename = value
                    elif key == 'fields':
                        # Decode the value and split by comma
                        fieldnames = unquote_plus(value).split(',')
                    else:
                        # Decode the value and add it to query_params
                        value = unquote_plus(value)
                        query_params[key] = value
            
        # Build dynamic query
        query = db.query(Business)
        
        # Apply name filter if it exists
        if original_params and not '=' in original_params:
            decoded_params = unquote_plus(original_params)  # Decode the search term
            query = query.filter(Business.name.ilike(f"%{decoded_params}%"))
            
        # Apply additional filters from query parameters
        for key, value in query_params.items():
            if hasattr(Business, key):
                query = query.filter(getattr(Business, key).ilike(f"%{value}%"))
        
        businesses = query.all()
        log.info(f"Found {len(businesses)} businesses matching criteria")
        
        if not businesses:
            log.error(f"404 - No businesses found matching criteria")
            raise HTTPException(status_code=404, detail=f"No businesses found matching criteria: {params}")
        
        if not fieldnames:
            # Default fieldnames if not provided
            fieldnames = [
                'name',
                'address',
                'address2',
                'city',
                'state',
                'zip',
                'phone',
                'email',
                'website',
                'industry'
            ]

        response = export.to_csv(businesses, fieldnames, filename)
        log.info(f"Exported {len(businesses)} businesses to CSV")
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