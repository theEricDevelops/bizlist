import os
import sys
path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(path)

import requests
from sqlalchemy.orm import Session

from app.core.config import config
from app.core.database import get_db

from app.services.logger import Logger
from app.services.source import add_or_find_source
from app.services.scraping import ScrapingService

from app.schemas.source import SourceData, SourceSchema
from app.schemas.location import ZipCodeSchema

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys

from bs4 import BeautifulSoup

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

log = Logger('scraper-owenscorning')
html_log = Logger('scraper-ownescornning-html')

class OwensCorningResult(BaseModel):
    id: str = Field(description="Unique identifier for the listing")
    name: str = Field(description="Name of the business")
    address: str = Field(description="Address of the business")
    address2: Optional[str] = Field(default=None, description="Secondary address line")
    city: str = Field(description="City of the business")
    state: str = Field(description="State of the business")
    zip: str = Field(description="Zip code of the business")
    phone: str = Field(description="Phone number of the business")
    website: str = Field(description="Website of the business")
    tags: Optional[List[str]] = Field(default=None, description="Tags associated with the business")
    source_id: str = Field(description="Source ID for the data")

RADIUS_OPTIONS = { 20, 50, 100 }

class OwensCorningScraper:
    def __init__(self, location: str | int | dict, radius: int = 20, db: Session = None, source: SourceSchema = None):
        if radius not in RADIUS_OPTIONS:
            valid_options = ", ".join(str(r) for r in RADIUS_OPTIONS)
            log.error(f"Invalid radius: {radius}. Valid options are: {valid_options}")
        self.base_url = "https://www.owenscorning.com/en-us/roofing/contractors"
        self.detail_url = "https://www.owenscorning.com/en-us/roofing/contractors/contractor-profile/"
        self.db = db if db else next(get_db())
        log.debug(f"Database connection established: {self.db}")
        self.scraper = ScrapingService()
        log.debug(f"Scraping service initialized: {self.scraper}")
        self.location = self.scraper.set_location(location, db)
        log.debug(f"Location set: {self.location}")
        self.radius = radius
        log.debug(f"Radius set: {self.radius}")
        self.source = source if source else add_or_find_source(SourceSchema(name="Owens Corning", url=self.base_url), self.db)
        log.debug(f"Source set: {self.source}")
        self.driver = self.scraper.setup_driver()
        log.debug(f"Scraper initialized with location: {self.location}, radius: {self.radius}, source: {self.source}")
    
    def get_listings(self, location: dict, radius: int = 20) -> List[OwensCorningResult]:
        """Get listings from Owens Corning based on location and radius."""
        log.info(f"Getting listings for {location} with radius {radius}")
        self.scraper.set_geolocation(self.driver, location, self.db)
        self.driver.get(self.base_url)
        
        try:
            # Wait for the page to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            log.info("Page loaded successfully.")
            
            # Handle iframe if present
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            if iframes:
                log.info(f"Iframe detected: {iframes[0].get_attribute('src')}")
                
                # Switch to iframe
                WebDriverWait(self.driver, 15).until(
                    EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, "iframe"))
                )
                
                # Look for any input field that might accept zip codes
                try:
                    # Try different possible selectors for zip input
                    selectors = ["input#zip", "input[type='text']", "input.zip-input"]
                    
                    for selector in selectors:
                        try:
                            zip_input = WebDriverWait(self.driver, 5).until(
                                EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
                            )
                            log.info(f"Found zip input with selector: {selector}")
                            zip_input.clear()
                            zip_input.send_keys(location["zipCode"])
                            
                            # Look for a submit button or hit Enter
                            try:
                                submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                                submit_button.click()
                            except:
                                zip_input.send_keys(Keys.RETURN)
                                
                            log.info("Submitted zip code in iframe")
                            break
                        except:
                            continue
                    
                    # Wait for iframe content to process
                    import time
                    time.sleep(3)
                    
                except Exception as e:
                    log.warning(f"Error entering zip code in iframe: {e}")
                
                # Switch back to main content
                self.driver.switch_to.default_content()
                log.info("Switched back to main content")
                
                # Give the page a moment to update after iframe interaction
                time.sleep(2)
            
            # Now wait for search results container
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.contractor-list"))
                )
                log.info("Found contractor list container")
                
                # If radius dropdown exists, set it
                try:
                    radius_dropdown = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "select#select-radius"))
                    )
                    self.driver.execute_script("arguments[0].click();", radius_dropdown)
                    
                    radius_option = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, f"//option[@value='{radius}']"))
                    )
                    self.driver.execute_script("arguments[0].click();", radius_option)
                    log.info(f"Set radius to {radius}")
                    
                    # Wait for results to update after radius change
                    time.sleep(2)
                except Exception as e:
                    log.warning(f"Couldn't set radius: {e}")
                
                # Get contractors
                contractors = self.driver.find_elements(By.CLASS_NAME, "contractor")
                log.info(f"Found {len(contractors)} contractors")
                return contractors
                
            except TimeoutException as e:
                log.error(f"Timeout waiting for contractor list: {e}")
                return []
                
        except Exception as e:
            log.error(f"Error in scraping process: {e}")
            return []

if __name__ == "__main__":
    # Example usage
    location = {"zipCode": "30115"}
    radius = 20
    db = next(get_db())
    scraper = OwensCorningScraper(location=location, radius=radius)
    listings = scraper.get_listings(location, radius)
    for listing in listings:
        print(listing.text)