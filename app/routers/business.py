from urllib.parse import unquote_plus

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi import Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import Dict, Any
from fastapi import Query

from app.core.database import get_db

from app.services.logger import Logger
from app.services.exporter import Exporter
from app.services.business import BusinessService

from app.models.contact import Business
from app.schemas.core import APIResponse, BusinessResponse
from app.schemas.contact import BusinessSchema, BusinessSchemaCreate, BusinessSchemaRead

log = Logger('router-business', log_level='DEBUG')

business_router = APIRouter()

@business_router.post("")
async def create_business(business: BusinessSchemaCreate, db: Session = Depends(get_db)):
    """Create a new business."""
    try:
        bus_service = BusinessService()
        code, status, error_list, parameters, result = bus_service.add(db=db, data=business.model_dump())

        return JSONResponse(
            status_code=code,
            content={
                "status": status,
                "code": code,
                "errors": error_list,
                "params": parameters,
                "data": result
            }
        )
    except SQLAlchemyError as e:
        log.error(f"Error creating business: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": 500,
                "errors": [str(e)],
                "params": business.model_dump(),
                "data": None
            }
        )
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": 500,
                "errors": [str(e)],
                "params": business.model_dump(),
                "data": None
            }
        )

@business_router.get("", response_model=BusinessResponse)
def read_businesses(request: Request, db: Session = Depends(get_db)):
    """Read all businesses which match the parameters passed."""
    query_params: Dict[str, Any] = dict(request.query_params)

    bus_service = BusinessService()
    code, status, error_list, parameters, results = bus_service.get(db=db, params=query_params)
    return JSONResponse(
        status_code=code,
        content={
            "status": status,
            "code": code,
            "errors": error_list,
            "params": parameters,
            "data": results
        }
    )

        
@business_router.get("/export")
def read_businesses_export(db: Session = Depends(get_db)):
    """Read all businesses for export."""
    export = Exporter()
    try:
        businesses = db.query(Business).all()
        log.info(f"Exporting {len(businesses)} businesses to CSV")
        response = export.to_csv(businesses)
        return FileResponse(path=response['path'], media_type='text/csv', filename=response['filename'])
    except FileNotFoundError as e:
        log.error(f"File not found: {e}")
        raise HTTPException(status_code=404, detail=f"File not found: {e}")
    except PermissionError as e:
        log.error(f"Permission error: {e}")
        raise HTTPException(status_code=403, detail=f"Permission error: {e}")
    except SQLAlchemyError as e:
        log.error(f"Error reading businesses for export: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
    
@business_router.get("/export/{params}")
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
        return FileResponse(path=response['path'], media_type='text/csv', filename=response['filename'])
    except FileNotFoundError as e:
        log.error(f"File not found: {e}")
        raise HTTPException(status_code=404, detail=f"File not found: {e}")
    except PermissionError as e:
        log.error(f"Permission error: {e}")
        raise HTTPException(status_code=403, detail=f"Permission error: {e}")
    except ValueError as e:
        log.error(f"Value error: {e}")
        raise HTTPException(status_code=400, detail=f"Value error: {e}")
    except TypeError as e:
        log.error(f"Type error: {e}")
        raise HTTPException(status_code=400, detail=f"Type error: {e}")
    except KeyError as e:
        log.error(f"Key error: {e}")
        raise HTTPException(status_code=400, detail=f"Key error: {e}")
    except AttributeError as e:
        log.error(f"Attribute error: {e}")
        raise HTTPException(status_code=400, detail=f"Attribute error: {e}")
    except SQLAlchemyError as e: 
        log.error(f"Error reading businesses for export: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

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