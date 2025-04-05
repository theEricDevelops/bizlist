from urllib.parse import unquote_plus
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi import Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, HttpUrl, EmailStr
from fastapi import Query

from app.core.database import get_db

from app.services.logger import Logger
from app.services.exporter import Exporter

from app.models.contact import Business
from app.schemas.core import APIResponse, BusinessResponse
from app.schemas.contact import BusinessSchema, BusinessSchemaRef, BusinessSchemaRead

log = Logger('router-business', log_level='DEBUG')

business_router = APIRouter()

class BusinessResponse(BaseModel):
    status_code: int
    message: Literal['Pending', 'Success', 'Error']
    parameters: Optional[dict] = None
    errors: Optional[dict] = None
    data: Optional[List[BusinessSchema]] = None

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
        response = APIResponse(
            code=500,
            status="error",
            errors={"message": f"Database error: {e}"},
            params={}
        )
        raise HTTPException(status_code=500, detail=response.model_dump())
    except Exception as e:
        db.rollback()
        log.error(f"Unexpected error: {e}")
        response = APIResponse(
            code=500,
            status="error",
            errors={"message": f"Unexpected error: {e}"},
            params={}
        )
        raise HTTPException(status_code=500, detail=response.model_dump())

@business_router.get("/list")
def read_all_businesses(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """Read ALl Businesses."""
    log.info(f"Read all businesses, skip: {skip}, limit: {limit}")
    query_params = {
        "skip": skip,
        "limit": limit
    }

    try:
        businesses = db.query(Business).offset(skip).limit(limit).all()
        log.info(f"Serving {len(businesses)} business results.")

        if not businesses:
            log.warning("No businesses found")
            return []
        
        data = []
        for business in businesses:
            business_dict = business.__dict__.copy()
            for key in business_dict:
                if business_dict[key] == '':
                    business_dict[key] = None
            if business_dict['notes'] is not List:
                business_dict['notes'] = [business_dict['notes']]
            data.append(business_dict)
        
        business_models = [BusinessSchemaRead.model_validate(business) for business in data]

        business_list = []
        for model in business_models:
            business_dict = model.model_dump()
            # Convert any UUID objects to strings
            for key, value in business_dict.items():
                if isinstance(value, UUID):
                    business_dict[key] = str(value)
            business_list.append(business_dict)
        
        return JSONResponse(
            status_code=200, 
            content= {
                "status": 'success',
                "code": 200,
                "params": query_params,
                "data": {
                    "total_results": len(businesses),
                    "businesses": business_list
                }
            }, headers={"server": "BizList API"})
    except SQLAlchemyError as e:
        log.error(f"Error reading businesses: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@business_router.get("/search", response_model=BusinessResponse)
def read_businesses(request: Request, db: Session = Depends(get_db)):
    """Read all businesses which match the parameters passed."""
    query_params: Dict[str, Any] = dict(request.query_params)
    log.debug(f"Query parameters: {query_params}")

    try:
        if query_params:
            # Build dynamic query
            query = db.query(Business)

            limit = int(query_params.pop('limit', 10))
            skip = int(query_params.pop('skip', 0))
            
            # Apply filters from query parameters
            invalid_params = []
            for key, value in query_params.items():
                if hasattr(Business, key):
                    query = query.filter(getattr(Business, key).ilike(f"%{value}%"))
                else:
                    invalid_params.append(key)
            
            if invalid_params:
                log.warning(f"Invalid query parameters: {invalid_params}")
                response = APIResponse(
                    code=400,
                    status="error",
                    errors={"invalid_params": invalid_params},
                    params=query_params
                )
                
                return JSONResponse(status_code=400, content=response.model_dump())
                    
            
            query = query.offset(skip).limit(limit)
            businesses = query.all()
            log.info(f"Found {len(businesses)} businesses matching criteria")
            
            
        else:
            log.debug("No query parameters provided. Displaying error message.")
            response = APIResponse(
                code=400,
                status="error",
                errors={"message": "No search parameters provided."},
                params=query_params
            )
            return JSONResponse(status_code=400, content=response.model_dump())

        if not businesses:
            log.error(f"404 - No businesses found matching criteria")
            response = APIResponse(
                code=404,
                status="error",
                errors={"message": "No businesses found matching criteria."},
                params=query_params
            )
            return JSONResponse(status_code=404, content=response.model_dump())

        
        log.debug(f"Business objects: {businesses}")
        log.info(f"Returning {len(businesses)} businesses")

        business_list = []
        for business in businesses:
            business_dict = business.__dict__.copy()
            business_dict.pop('_sa_instance_state', None)

            keys_to_process = list(business_dict.keys())

            processed_dict = {}
            for key in keys_to_process:
                value = business_dict[key]
                
                if value == '' or value is None:
                    continue

                if isinstance(value, UUID):
                    processed_dict[key] = str(value)
                else:
                    processed_dict[key] = value

            try:
                business_model = BusinessSchemaRead.model_validate(processed_dict)

                business_data = business_model.model_dump()

                for key, value in business_data.items():
                    if isinstance(value, UUID):
                        business_data[key] = str(value)

                business_list.append(business_data)
            except Exception as e:
                log.error(f"Error validating business model: {e}")
                
                for key, value in processed_dict.items():
                    if isinstance(value, UUID):
                        processed_dict[key] = str(value)
                business_list.append(processed_dict)
        params = dict(request.query_params)
        params.update({"limit": limit, "skip": skip})
        return JSONResponse(
            status_code=200,
            content= {
                "status": 'success',
                "code": 200,
                "params": params,
                "data": {
                    "total_results": len(businesses),
                    "businesses": business_list
                }
            }
        )
    except SQLAlchemyError as e:
        log.error(f"Error reading businesses: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": 500,
                "errors": {"message": f"Database error: {e}"},
                "params": query_params
            }
        )
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": 500,
                "errors": {"message": f"Unexpected error: {e}"},
                "params": query_params
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