from fastapi import APIRouter, Depends, HTTPException
import requests
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.config import config

from app.services.logger import Logger
from app.services.exporter import Exporter
from app.services.api_clients.serpapi import SerpAPI
from app.core.database import get_db

from app.models.contact import Business
from app.schemas.serpapi import SerpAPILocalAdsResult, SerpAPILocalAdsQuery

log = Logger('router-serpapi')

serpapi_router = APIRouter()

@serpapi_router.get("/local-ads/{q}", response_model=SerpAPILocalAdsResult)
def get_serpapi(query: SerpAPILocalAdsQuery, db: Session = Depends(get_db)):
    """Get Local Ads Results from SerpAPI."""
    try:
        # Validate the query parameters
        if not query.query:
            raise HTTPException(status_code=400, detail="Query parameter is required")
        
        # Call the SerpAPI client to get the local ads results
        serpapi = SerpAPI()
        result = serpapi.get_local_ads(query)

        # Process the result as needed (e.g., save to database, etc.)
        # Here we just return the result for demonstration purposes

        return result
    except SQLAlchemyError as e:
        log.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    except requests.exceptions.RequestException as e:
        log.error(f"Request error: {e}")
        raise HTTPException(status_code=500, detail="Request error")