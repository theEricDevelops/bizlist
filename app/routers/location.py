from urllib.parse import unquote_plus

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi import Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db

from app.services.logger import Logger
from app.services.location import LocationService
from app.models.location import ZipCode
from app.schemas.location import ZipCodeSchema

log = Logger('router-location', log_level='DEBUG')

location_router = APIRouter()

@location_router.get("/zip/{zip_code}", response_model=ZipCodeSchema)
def get_location_by_zip(zip_code: str, db: Session = Depends(get_db)):
    """Get location by zip code."""
    try:
        location_service = LocationService(db)
        location = location_service.get(zip_code)
        if not location:
            raise HTTPException(status_code=404, detail="Location not found")
        return location
    except SQLAlchemyError as e:
        log.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@location_router.get("/city/{city}/{state}", response_model=ZipCodeSchema)
def get_location_by_city(city: str, state: str, db: Session = Depends(get_db)):
    """Get location by city and state."""
    try:
        location_service = LocationService(db)
        locations = location_service.get(f"{city}, {state}")
        if not locations:
            raise HTTPException(status_code=404, detail="Locations not found")
        return locations
    except SQLAlchemyError as e:
        log.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")