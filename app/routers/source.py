from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import Dict, Any

from fastapi.responses import JSONResponse

from app.core.database import get_db
from app.models.source import Source
from app.schemas.source import SourceSchemaRef
from app.services.logger import Logger
from app.services.source import SourceService

from app.schemas.core import APIResponse, SourceResponse

log = Logger('router-source', log_level='DEBUG')

source_router = APIRouter()

@source_router.get("")
def get_sources(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    search: str = None,
):
    """Get a list of sources."""
    try:
        sources = SourceService()
        status, code, error_list, parameters, results = sources.get(db=db, skip=skip, limit=limit, search=search)
        log.debug(f"Code: {code}, Status: {status}, Errors: {error_list}, Parameters: {parameters}, Results: {results}")

        response = SourceResponse(
            status=status,
            code=code,
            errors=error_list,
            params=parameters,
            data=results
        )

        return JSONResponse(status_code=code, content=response.model_dump())
    except SQLAlchemyError as e:
        log.error(f"Error getting sources: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": 500,
                "errors": [str(e)],
                "params": {},
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
                "params": {},
                "data": None
            }
        )

@source_router.post("")
def add_source(
    source: SourceSchemaRef,
    db: Session = Depends(get_db),
):
    """Add a new source."""
    try:
        sources = SourceService()
        status, code, error_list, parameters, results = sources.add(db=db, source=source)
        log.debug(f"Code: {code}, Status: {status}, Errors: {error_list}, Parameters: {parameters}, Results: {results}")

        response = SourceResponse(
            status=status,
            code=code,
            errors=error_list,
            params=parameters,
            data=results
        )

        return JSONResponse(status_code=code, content=response.model_dump())
    except SQLAlchemyError as e:
        log.error(f"Error adding source: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": 500,
                "errors": [str(e)],
                "params": {},
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
                "params": {},
                "data": None
            }
        )