# app/services/api_clients/serpapi.py

import os
import requests
from urllib.parse import urlencode
from app.schemas.serpapi import SerpAPILocalAdsQuery, SerpAPILocalAdsResult, Hours, Week
from typing import Optional

from app.services.logger import Logger
from app.core.config import config

log = Logger('apiclient-serpapi')

class SerpAPI:
    def __init__(self, api_key: str = None):
        if api_key:
            self.api_key = api_key
        else:
            try:
                self.api_key = config.settings['SERP_API_KEY'] or os.getenv("SERP_API_KEY")
            except KeyError:
                log.error("SERPAPI key not found in environment variables or config.")
                raise ValueError("API key not found. Please set the SERP_API_KEY environment variable.")
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
        filtered_params = {k: v for k, v in params.items() if v is not None}

        encoded_params = urlencode(filtered_params)

        url = f"{self.base_url}{encoded_params}"

        return url
    
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
    
    def get_local_ads(self, query: SerpAPILocalAdsQuery) -> Optional[SerpAPILocalAdsResult]:
        """Perform a local ads search using the SerpAPI."""
        try:
            params = query.model_dump(exclude_none=True)
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