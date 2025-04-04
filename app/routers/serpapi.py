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
from app.services.location import LocationService
from app.core.database import get_db

from app.models.location import ZipCode
from app.schemas.location import ZipCodeSchema

from app.schemas.serpapi import SerpAPILocalAdsResult, SerpAPILocalAdsQuery

log = Logger('router-serpapi')

serpapi_router = APIRouter()

location = LocationService()

@serpapi_router.get("/local-ads", response_model=SerpAPILocalAdsResult)
def get_serpapi(query: SerpAPILocalAdsQuery = Depends(), db: Session = Depends(get_db)):
    """Get Local Ads Results from SerpAPI."""
    try:
        # Validate the query parameters
        if not query.q:
            raise HTTPException(status_code=400, detail="Query parameter is required")
        
        # Call the SerpAPI client to get the local ads results
        serpapi = SerpAPI()
        data_cid = None

        # Get the cid if not passed as a parameter
        if not query.data_cid:
            if query.zip:
                data_cid = location.get_google_cid(query.zip)
            elif query.city and query.state:
                data_cid = location.get_google_cid(f"{query.city}, {query.state}")
        else:
            # Verify if the cid is valid
            if not location.verify_google_cid(query.data_cid):
                raise HTTPException(status_code=400, detail="Invalid Google CID")
            data_cid = query.data_cid

        result = serpapi.get_local_ads(query)

        if not result:
            raise HTTPException(status_code=404, detail="No results found")
        


        return result
    except SQLAlchemyError as e:
        log.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    except requests.exceptions.RequestException as e:
        log.error(f"Request error: {e}")
        raise HTTPException(status_code=500, detail="Request error")