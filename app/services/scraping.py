import os, csv, re
import requests
from typing import List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from app.services.logger import Logger
from urllib.parse import urlparse
from app.models.location import CoverageZipList

log = Logger('service-scraping', log_level='INFO')
html_log = Logger('service-scraping-html')

class ScrapingService:
    def __init__(self):
        pass

    def setup_driver(sandbox: bool = False, headless: bool = False) -> webdriver.Chrome:
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
    
    def load_zip_code_data():
        """Loads zip code data from CSV into a dictionary mapping zip codes to (latitude, longitude)."""
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(project_dir, "data", "USZipsWithLatLon_20231227.csv")
        
        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                zip_data = {}
                for row in reader:
                    zip_code = row['postal code']
                    lat = float(row['latitude'])
                    lon = float(row['longitude'])
                    zip_data[zip_code] = (lat, lon)
                return zip_data
        except FileNotFoundError:
            log.error(f"CSV file not found: {csv_path}")
            return {}
        except KeyError as e:
            log.error(f"Missing column in CSV: {e}")
            return {}
        except ValueError as e:
            log.error(f"Error parsing CSV: {e}")
            return {}

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