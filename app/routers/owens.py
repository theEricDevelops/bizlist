from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.core.database import get_db_conn
from app.services.logger import Logger

from app.services.scrapers.owenscorning import OwensCorningScraper, OwensCorningResult
from app.schemas.location import ZipCodeSchema

from typing import List
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

log = Logger('router-owenscorning', log_level='DEBUG')

owenscorning = APIRouter()

@owenscorning.get("/{location}", response_model=List[OwensCorningResult])
def scrape_owenscorning(location: str, radius: int = 20):
    """
    Scrape Owens Corning contractor listings based on location and radius.
    """
    log.info(f"Scraping Owens Corning for location: {location}, radius: {radius}")

    db = get_db_conn()
    log.debug(f"Database connection established: {db}")

    try:
        log.debug(f"Setting up scraper for location: {location}, radius: {radius}")
        scraper = OwensCorningScraper(location=location)
        log.debug(f"Scraper initialized: {scraper}")
        listings = scraper.get_listings(location, radius, db)
        log.debug(f"Listings retrieved: {listings}")
        return listings
    except SQLAlchemyError as e:
        log.error(f"Database error: {e}")
        return JSONResponse(status_code=500, content={"message": "Database error occurred."})
    except Exception as e:
        log.error(f"An error occurred: {e}")
        return JSONResponse(status_code=500, content={"ERROR": f"An unexpected error occurred: {e}"})