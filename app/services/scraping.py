import re
import requests
from typing import List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from app.services.logger import Logger
from urllib.parse import urlparse
from app.models.location import CoverageZipList, ZipCode
from app.schemas.location import ZipCodeSchema
from app.core.database import get_db_conn

log = Logger('service-scraping', log_level='DEBUG')
html_log = Logger('service-scraping-html')

class ScrapingService:
    def __init__(self):
        pass

    def setup_driver(sandbox: bool = False, headless: bool = False, **kwargs) -> webdriver.Chrome:
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless")
        if not sandbox:
            options.add_argument("--no-sandbox")
            
        options.binary_location = r"C:\Users\eric\dev\bizlist\webdriver\chrome-win64\chrome.exe"
        chromedriver_path = r"C:\Users\eric\dev\bizlist\webdriver\chromedriver-win64\chromedriver.exe"
        service = ChromeService(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    
    def set_location(self, location: dict | str | int, db: Session) -> ZipCodeSchema:
        """Set the location for the scraper based on the provided input."""
        
        # Convert location into a dictionary if it's a string or integer
        if isinstance(location, str):
            if re.match(r'^\d{5}$', location):
                log.debug(f"Assuming location is a zip code: {location}")
                # Assuming it's a zip code
                location = {"zipCode": location}
            else:
                log.debug(f"Assuming location is a city/state: {location}")
                # Assuming it's a city/state
                parts = location.split(',')
                if len(parts) == 2:
                    city, state = map(str.strip, parts)
                    log.debug(f"Parsed city: {city}, state: {state}")
                    location = {"city": city, "state": state}
                else:
                    raise ValueError("Invalid location format. Expected 'city, state' or 'zipCode'.")
        
        if isinstance(location, int) and len(str(location)) == 5:
            log.debug(f"Assuming location is a zip code: {location}")
            # Assuming it's a zip code
            location = {"zipCode": str(location)}

        return self.get_zip_data(location, db)

    def get_zip_data(self, location: dict, db: Session) -> ZipCode:
        """Retrieve zip code data from the database."""
        try:
            log.info(f"Retrieving zip code data for location: {location}")
            db = next(get_db_conn())
            # Set geolocation if zip code is provided
            if "zipCode" in location:
                zip_data = db.query(ZipCode).filter_by(zip=location["zipCode"]).first()
                log.debug(f"Zip code data found: {zip_data}")
            elif "city" in location and "state" in location:
                zip_data = db.query(ZipCode).filter_by(city=location["city"], state=location["state"]).first()
                log.debug(f"Zip code data found: {zip_data}")
            else:
                log.warning("No zip code or city/state combo provided, not setting geolocation.")
                return None
            
            return zip_data
            
        except Exception as e:
            log.error(f"Error retrieving zip code data from database: {e}")
            return None

    def set_geolocation(self, driver: webdriver.Chrome, location: dict, db: Session) -> None:
        """Set the geolocation for the driver based on the provided location."""
        log.info(f"Setting geolocation for driver with location: {location}")

        zip_data: ZipCode = self.get_zip_data(location=location, db=db)

        if zip_data:
            lat = zip_data.latitude
            lon = zip_data.longitude
            driver.execute_cdp_cmd("Emulation.setGeolocationOverride", {
                "latitude": lat,
                "longitude": lon,
                "accuracy": 100
            })
            log.info(f"Set geolocation to lat: {lat}, lon: {lon} for zip code: {location['zipCode']}")
        else:
            log.warning(f"Zip code {location['zipCode']} not found in zip data.")
    
    def build_base_url(location: dict, radius: int) -> str:
        log.info(f"Building base URL for GAF with location: {location} and radius: {radius}")
        if "state" in location and "city" in location:
            url = f"https://www.gaf.com/en-us/roofing-contractors/residential/usa/{location['state']}/{location['city']}?distance={radius}"
        elif "zipCode" in location:
            url = f"https://www.gaf.com/en-us/roofing-contractors/residential?postalCode={location['zipCode']}&distance={radius}&countryCode=us"
        elif ("state" in location and "city" not in location) or ("city" in location and "state" not in location):
            raise ValueError("Both 'state' and 'city' are required if one is provided.")
        elif ("state" in location or "city" in location) and "zip" in location:
            raise ValueError("You need to provide either 'state' and 'city' or 'zip', not both.")
        else:
            raise ValueError("You need to provide either 'state' and 'city' or 'zip'.")
        log.debug(f"Built URL: {url}")
        return url

    def get_top_level_url(url: str) -> str:
        log.info(f"Extracting top-level URL from: {url}")
        try:
            parsed_url = urlparse(url)
            top_level_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            log.debug(f"Extracted top-level URL: {top_level_url}")
            return top_level_url
        except Exception as e:
            log.error(f"Error extracting top-level URL: {e}")
            return None

    def zips_by_state(db: Session, states: List[str]) -> List[str]:
        zip_codes = []
        for state in states:
            log.debug(f"Extracting ZIP codes for state: {state}")
            state_zips = db.query(CoverageZipList).filter(CoverageZipList.params.like(f'%area\': \'{state}\'%')).all()
            state_zips.sort()
            for zip_entry in state_zips:
                zip_codes.extend(zip_entry.zips.split(','))
        return zip_codes
    
    def get_html_from_url(url: str) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }
        try:
            log.info(f"Retrieving HTML from URL: {url}")
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            body_content = str(soup.body)
            log.debug(f"Response status code: {response.status_code}")
            html_log.debug(f"Response content: {response.content}")
            log.debug(f"Response headers: {response.headers}")
            return body_content
        except requests.RequestException as e:
            log.error(f"Error retrieving HTML from URL: {url}")
            log.error(e)
            return None
        except Exception as e:
            log.exception(f"An unexpected error occurred while retrieving HTML from URL: {url}")
            return None