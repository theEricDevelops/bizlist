import logging
from logging import Logger
import sys
import os
import requests
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional, List, Literal

load_dotenv()

# Configure logging
logging.basicConfig(level='DEBUG', filename='./logs/serpapi.log', filemode='w')
log = logging.getLogger(__name__)

# Load the API key from the environment variable
api_key = os.getenv("SERP_API_KEY")

class SupportedLanguage(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None

class Week(BaseModel):
    monday: Optional[str] = None
    tuesday: Optional[str] = None
    wednesday: Optional[str] = None
    thursday: Optional[str] = None
    friday: Optional[str] = None
    saturday: Optional[str] = None
    sunday: Optional[str] = None

class Hours(BaseModel):
    currently: Optional[str] = None
    week: Optional[Week] = None

class LocalAd(BaseModel):
    title: Optional[str] = None
    link: Optional[str] = None
    rating: Optional[float] = None
    reviews: Optional[int] = None
    phone: Optional[str] = None
    badge: Optional[str] = None
    type: Optional[str] = None
    service_area: Optional[str] = None
    years_in_business: Optional[int] = None
    bookings_nearby: Optional[int] = None
    thumbnail: Optional[str] = None
    hours: Optional[Hours] = None
    cid: Optional[str] = None
    bid: Optional[str] = None
    pid: Optional[str] = None
    serpapi_link: Optional[str] = None

class SerpAPILocalAdsQuery(BaseModel):
    q: str
    data_cid: str
    hl: Optional[str] = 'en'
    job_type: Optional[str] = None
    cid: Optional[str] = None
    bid: Optional[str] = None
    pid: Optional[str] = None
    engine: str = 'google_local_services'
    no_cache: Optional[bool] = False
    async_search: Optional[bool] = True
    zero_trace: Optional[bool] = False
    api_key: str
    output: Literal['JSON', 'html'] = 'JSON'

class SerpAPILocalAdsResult(BaseModel):
    search_metada: Optional[dict] = None
    search_parameters: Optional[dict] = None
    search_information: Optional[dict] = None
    local_ads: Optional[List[LocalAd]] = None
    
class SerpAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search?"
        self.engine = None

    def _build_query(self, query: str, data_cid: str, **kwargs) -> SerpAPILocalAdsQuery:
        return SerpAPILocalAdsQuery(
            q=query,
            data_cid=data_cid,
            api_key=self.api_key,
            **kwargs
        )
    
    def _build_url(self, params: SerpAPILocalAdsQuery) -> str:
        return self.base_url + "&".join([f"{k}={v}" for k, v in params.items() if v is not None])
    
    def _process_hours(self, hours_data: dict) -> Hours:
        """Process the hours data from the SerpAPI response."""
        if not hours_data:
            return Hours()
        
        week_data = hours_data.get("week")

        if not week_data:
            return Hours(currently=hours_data.get("currently"))
        
        week = {}
        for day in week_data:
            week.update(day)
        
        return Hours(currently=hours_data.get("currently"), week=Week(**week))
    
    def local_ads_search(self, query: SerpAPILocalAdsQuery) -> Optional[SerpAPILocalAdsResult]:
        """Perform a local ads search using the SerpAPI."""
        try:
            params = query.model_dump()
            print(f"Query Parameters: {params}")
            url = self._build_url(params)
            print(f"Request URL: {url}")
            response = requests.get(url)
            response.raise_for_status()
            print(f"Raw Response: {response.text}")
            log.debug(f"Raw Response: {response.text}")
            res = response.json()

            if "local_ads" in res:
                for ad in res["local_ads"]:
                    if "hours" in ad:
                        ad["hours"] = self._process_hours(ad["hours"])

            return SerpAPILocalAdsResult(**res)
        except requests.HTTPError as e:
            log.error(f"HTTP error occurred: {e}")
            return None
        except requests.RequestException as e:
            log.error(f"Request error occurred: {e}")
            return None
        except Exception as e:
            log.error(f"An error occurred: {e}")
            return None

if __name__ == "__main__":
    serp_api = SerpAPI(api_key)
    query = "painter"
    data_cid = "7260588484127004678"

    q = serp_api._build_query(query, data_cid)
    response = serp_api.local_ads_search(q)

    if response:
        print("Query response:")
        log.debug(f"Query response: {response.model_dump_json(indent=2)}")
        print(response.model_dump_json(indent=2))
    else:
        print("Query failed.")