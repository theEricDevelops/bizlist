from pydantic import BaseModel
from typing import Optional, List, Literal

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
    output: Literal['JSON', 'html'] = 'JSON'

class SerpAPILocalAdsResult(BaseModel):
    search_metada: Optional[dict] = None
    search_parameters: Optional[dict] = None
    search_information: Optional[dict] = None
    local_ads: Optional[List[LocalAd]] = None