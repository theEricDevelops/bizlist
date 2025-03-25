import os
import re
import requests
import uuid
from schemas import SourceData, SourceSchema, BusinessSchema
from models import Business, Contact, Source, BusinessSource

from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select
from openai import OpenAI

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import TimeoutException

from bs4 import BeautifulSoup

import logging
import time
import csv  # Added for CSV handling

from urllib.parse import urlparse

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(PROJECT_DIR, os.getenv("DOWNLOAD_DIR", "downloads"))
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Configure logging
log_folder = os.getenv("LOG_FOLDER", "/logs")
log_folder = os.path.abspath(log_folder)
log_file = os.path.join(log_folder, os.getenv("LOG_FILE", "bizlist.log"))
log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
os.makedirs(log_folder, exist_ok=True)

log_level_str = os.getenv("LOG_LEVEL", "DEBUG")
log_level = getattr(logging, log_level_str.upper(), logging.DEBUG)

logger = logging.getLogger(__name__)
logger.setLevel(log_level)
lh = logging.FileHandler(log_file, mode="w")
lh.setFormatter(logging.Formatter(log_format))
logger.addHandler(lh)

html_output_file = os.path.join(log_folder, "html_output.log")
html_lh = logging.FileHandler(html_output_file, mode="w")
html_lh.setFormatter(logging.Formatter(log_format))
html_logger = logging.getLogger("html")
html_logger.setLevel(log_level)
html_logger.addHandler(html_lh)

def setup_driver() -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    #options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.binary_location = r"C:\Users\eric\dev\bizlist\webdriver\chrome-win64\chrome.exe"
    chromedriver_path = r"C:\Users\eric\dev\bizlist\webdriver\chromedriver-win64\chromedriver.exe"
    service = ChromeService(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)
    return driver

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
        logger.error(f"CSV file not found: {csv_path}")
        return {}
    except KeyError as e:
        logger.error(f"Missing column in CSV: {e}")
        return {}
    except ValueError as e:
        logger.error(f"Error parsing CSV: {e}")
        return {}

def get_zips_to_search_by_states(db: Session, states: List[str], radius: int = 25) -> List[str]:
    for state in states:
        logger.debug(f"Extracting ZIP codes for state: {state}")
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
        logger.info(f"Retrieving HTML from URL: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        body_content = str(soup.body)
        logger.debug(f"Response status code: {response.status_code}")
        html_logger.debug(f"Response content: {response.content}")
        logger.debug(f"Response headers: {response.headers}")
        return body_content
    except requests.RequestException as e:
        logger.error(f"Error retrieving HTML from URL: {url}")
        logger.error(e)
        return None
    except Exception as e:
        logger.exception(f"An unexpected error occurred while retrieving HTML from URL: {url}")
        return None

def formatPhone(number: str) -> str:
    number = number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace(".", "").replace("+", "")
    number = number.split("tel:")[-1] if number.startswith("tel:") else number
    if len(number) == 10:
        logger.debug(f"Returning phone number: {number}")
        return number
    elif len(number) == 11 and number[0] == "1":
        logger.debug(f"Formatting phone number: {number}")
        return number[1:]
    else:
        logger.warning(f"Invalid phone number: {number}")
        return None

def formatZipCode(zip_code: str) -> str:
    zip_code = zip_code.replace("-", "").replace(" ", "")
    if (len(zip_code) == 5 or len(zip_code) == 9) and zip_code.isdigit():
        logger.debug(f"Returning ZIP code: {zip_code}")
        return zip_code
    else:
        logger.warning(f"Invalid ZIP code: {zip_code}")
        return None

def formatWebsite(website: str) -> str:
    if not website:
        logger.debug(f"No website found")
        return None
    website = website.strip()
    url_pattern = r"^(?:http(s)?:\/\/)?[\w.-]+(?:\.[\w\.-]+)+[\w\-\._~:/?#[\]@!\$&'\(\)\*\+,;=.]+$"
    match = re.match(url_pattern, website, re.IGNORECASE)
    if match:
        if not website.startswith("http"):
            website = f"https://{website}"
        logger.debug(f"Returning website: {website}")
        return website
    elif match is None:
        logger.debug(f"No website found")
        return None
    else:
        logger.warning(f"Invalid website: {website}")
        return None

def formatEmail(email: str) -> str:
    if not email:
        logger.debug(f"No email found")
        return None
    email = email.strip()
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    match = re.match(email_pattern, email)
    if match:
        logger.debug(f"Returning email: {email}")
        return email
    else:
        logger.warning(f"Invalid email: {email}")
        return None

def get_address_parts(address_str: str) -> Tuple[str, str, str, str, str]:
    logger.debug(f"Parsing address: {address_str}")
    address_str = re.sub(r'\s+', ' ', address_str.strip())
    address_str = re.sub(r',+', ',', address_str)
    country_pattern = r'(,\s*)?(US|USA|United States|U\.S\.|U\.S\.A\.)$'
    country_match = re.search(country_pattern, address_str, re.IGNORECASE)
    if country_match:
        address_str = address_str[:country_match.start()].strip(', ')
    zip_pattern = r'(\d{5}(?:-\d{0,4})?|\d{4}|\d{6})$'
    zip_match = re.search(zip_pattern, address_str)
    if zip_match:
        zip_code = zip_match.group(0)
        address_no_zip = address_str[:zip_match.start()].strip(', ')
    else:
        zip_code = ''
        address_no_zip = address_str.strip(', ')
    if not address_no_zip:
        return (address_no_zip, '', '', '', zip_code)
    state_pattern = r'(?:,?\s*)([A-Z]{2}|New York|General Delivery)$'
    state_match = re.search(state_pattern, address_no_zip)
    if state_match:
        state = state_match.group(1)
        address_no_state = address_no_zip[:state_match.start()].strip(', ')
    else:
        state = ''
        address_no_state = address_no_zip.strip(', ')
    if not address_no_state:
        return (address_no_state, '', '', state, zip_code)
    parts = [p.strip() for p in address_no_state.split(',')]
    if len(parts) >= 2:
        city = parts[-1]
        address_parts = ' '.join(parts[:-1])
    else:
        words = address_no_state.split()
        if len(words) > 1:
            city = words[-1]
            address_parts = ' '.join(words[:-1])
        else:
            city = ''
            address_parts = address_no_state
    address1 = address_parts
    address2 = ''
    secondary_units = r'(Apt|Suite|Ste|Unit|Dept|#|No|Number|Floor|Flr)\s*[A-Za-z0-9-]+'
    secondary_match = re.search(secondary_units, address1, re.IGNORECASE)
    if secondary_match:
        address2 = address1[secondary_match.start():].strip()
        address1 = address1[:secondary_match.start()].strip()
    else:
        building_pattern = r'(Building|Bldg|Park|Pk|Office)\s+[A-Za-z0-9\s]+'
        if re.search(r'^\d+\s+[A-Za-z]+|^(RR|HC|PO|P\.O\.)', address1, re.IGNORECASE):
            building_match = re.search(building_pattern, address1, re.IGNORECASE)
            if building_match:
                address2 = address1[building_match.start():].strip()
                address1 = address1[:building_match.start()].strip()
    if state == "General Delivery":
        city = "General Delivery"
        state = ''
        address1 = address1 if address1 else "General Delivery"
        address2 = ''
    logger.debug(f"Extracted address parts: {address1}, {address2}, {city}, {state}, {zip_code}")
    return (address1, address2, city, state, zip_code)

def ask_ai_for_contact_info(client: OpenAI, system_message: str, info: Business | Contact, model: str) -> Dict:
    """Sends a prompt to the AI model to attempt to find contact info using tools."""
    completion = client.chat.completions.create(
        model="grok-2-latest",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": info.to_json()},
        ],
    )
    logger.debug(f"AI response: {completion}")
    response = completion.choices[0].message.content
    return response

def get_complete_contact_info(info: Business | Contact) -> Dict:
    system_message = """
        You are a web scraping expert. You will receive a JSON object string with any combination of the following company information:

        - name: string (company name)
        - phone: string (company phone)
        - email: string (company email)
        - address: string (company address)
        - website: string (company website)
        - industry: string (company industry)

        Your task is to search the web to complete the remaining fields and to attempt to find the owner's information.

        You have access to the following functions:
        - search_web(query: str) -> List[Dict[str, str]]: Searches the web for the query and returns a list of results, each with 'title', 'url', and 'snippet'.
        - get_webpage(url: str) -> str: Retrieves the HTML content of the URL.
        - extract_text(html: str, selector: str) -> str: Extracts text from the HTML using the CSS selector.
        - find_patterns(text: str, pattern: str) -> List[str]: Finds all matches of the regex pattern in the text.
        - extract_structured_data(html: str) -> Dict: Extracts structured data (JSON-LD or microdata) from the HTML.

        Use these functions to gather the required information.

        Your output should be a JSON object with the following fields:
        - company_name: string
        - company_phone: string
        - company_email: string
        - company_address: string
        - company_website: string
        - company_industry: string
        - owner_name: string
        - owner_phone: string
        - owner_email: string
        - owner_address: string
        - owner_linkedin: string

        If you cannot find a particular piece of information, set its value to null.
    """
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        raise ValueError("XAI_API_KEY environment variable not set.")
        return None
    client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
    logger.info("Sending info to LLM for contact info...")
    model = "grok-2-latest"
    response = ask_ai_for_contact_info(client, system_message, info, model)
    return response

def update_business(db: Session, business: Business, data: BusinessSchema) -> Business:
    business.name = data.name
    business.industry = data.industry
    business.email = data.email
    business.phone = data.phone
    business.address = data.address
    business.address2 = data.address2
    business.city = data.city
    business.state = data.state
    business.zip = data.zip
    business.website = data.website
    business.notes = data.notes
    for source_id in data.sources:
        if source_id not in [bs.source_id for bs in business.sources]:
            business.sources.append(source_id)
    db.commit()
    db.refresh(business)
    logger.info(f"Updated business: {business.name} (ID: {business.id})")
    return business

def insert_company_data(db: Session, company: SourceData):
    source = db.execute(select(Source).where(Source.id == company.source_id)).scalar_one_or_none()
    data = company.data
    name = str(data.get("name")).capitalize()
    industry = str(data.get("industry")).capitalize() or ""
    email = formatEmail(data.get("email")) or ""
    phone_number = formatPhone(data.get("phone")) or ""
    address, address2, city, state, zip = get_address_parts(data.get("address"))
    zip = formatZipCode(zip) or ""
    website = formatWebsite(data.get("website")) or ""
    business = Business(
        name=name, industry=industry, email=email, phone=phone_number,
        address=address, address2=address2, city=city, state=state, zip=zip,
        website=website, notes=str(data)
    )
    existing_business = db.query(Business).filter(Business.name == name).first()
    if existing_business:
        logger.info(f"Found existing business: {name} (ID: {existing_business.id})")
        updated_business = update_business(db, existing_business, business)
        db.refresh(updated_business)
        existing_business_source = db.query(BusinessSource).filter(
            BusinessSource.business_id == existing_business.id,
            BusinessSource.source_id == company.source_id
        ).first()
        if not existing_business_source and source:
            business_source = BusinessSource(business_id=existing_business.id, source_id=source.id)
            db.add(business_source)
        db.commit()
        return {"existing": True, "business": updated_business}
    else:
        logger.debug(f"Adding new business: {business}")    
        db.add(business)
        db.flush()
        if source:
            business_source = BusinessSource(business_id=business.id, source_id=source.id)
            db.add(business_source)
        db.commit()
        return {"existing": False, "business": business}

def build_base_url(location: dict, radius: int) -> str:
    logger.info(f"Building base URL for GAF with location: {location} and radius: {radius}")
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
    logger.debug(f"Built URL: {url}")
    return url

def get_top_level_url(url: str) -> str:
    logger.info(f"Extracting top-level URL from: {url}")
    try:
        parsed_url = urlparse(url)
        top_level_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        logger.debug(f"Extracted top-level URL: {top_level_url}")
        return top_level_url
    except Exception as e:
        logger.error(f"Error extracting top-level URL: {e}")
        return None

def add_or_find_source(db: Session, source: SourceSchema) -> uuid.UUID:
    source_name = source.name
    source_url = source.url
    existing_source = db.query(Source).filter(Source.name == source_name).first()
    if not existing_source:
        new_source = Source(name=source_name, url=source_url)
        db.add(new_source)
        db.commit()
        db.refresh(new_source)
        logger.info(f"Added new source: {new_source.name} (ID: {new_source.id})")
        return new_source.id
    else:
        logger.info(f"Found existing source: {existing_source.name} (ID: {existing_source.id})")
        return existing_source.id

def get_total_results(driver: webdriver.Chrome, url: str) -> int:
    try:
        logger.info(f"Getting total results from URL: {url}")
        driver.get(url)
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                WebDriverWait(driver, 20, poll_frequency=1).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "contractor-listing__wrapper"))
                )
                break
            except TimeoutException as e:
                if attempt == max_attempts:
                    logger.error(f"Timeout waiting for elements after {max_attempts} attempts.")
                    driver.quit()
                    return 0
                else:
                    logger.warning(f"Timeout waiting for elements (attempt {attempt}/{max_attempts}). Retrying url {url}...")
                    time.sleep(5)
                    driver.refresh()
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        body_content = soup.body
        html_logger.debug(f"Response body: {body_content}")
        query_summary = body_content.find("div", class_="query-summary")
        if query_summary:
            total_results_str = query_summary.text.strip().split("of ")[1].split(" ")[0]
            try:
                total_results = int(total_results_str)
                logger.info(f"Total results: {total_results}")
                return total_results
            except (ValueError, IndexError):
                logger.warning("Could not extract total results.")
                return 0
        elif body_content.find("div", class_="error-message"):
            logger.warning("No results found.")
            return 0
        else:
            logger.warning("Could not find query summary.")
            return 0
    except requests.RequestException as e:
        logger.error(f"Error getting total results: {e}")
        if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 403:
            logger.error("GAF is blocking our requests. Please try again later.")
        return 0
    except Exception as e:
        logger.exception(f"An unexpected error occurred while getting total results: {e}")
        return 0

def scrape_gaf(driver: webdriver.Chrome, url: str, page_num: int = 1) -> List[Dict]:
    if page_num > 1:
        url += f"#firstResult={10 * (page_num - 1)}"
    try:
        logger.info(f"Scraping GAF with URL: {url}")
        driver.get(url)
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                WebDriverWait(driver, 20, poll_frequency=1).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "certification-card"))
                )
                break
            except TimeoutException as e:
                if attempt == max_attempts:
                    logger.error(f"Timeout waiting for elements after {max_attempts} attempts.")
                    driver.quit()
                    return []
                else:
                    logger.warning(f"Timeout waiting for elements (attempt {attempt}/{max_attempts}). Retrying...")
                    time.sleep(5)
                    driver.refresh()
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        body_content = soup.body
        html_logger.debug(f"Response body: {body_content}")
        query_summary = body_content.find("div", class_="query-summary")
        if query_summary:
            total_results_str = query_summary.text.strip().split("of ")[1].split(" ")[0]
            try:
                total_results = int(total_results_str)
                logger.info(f"Total results: {total_results}")
            except (ValueError, IndexError):
                logger.warning("Could not extract total results.")
                total_results = 0
        else:
            logger.warning("Could not find query summary.")
            total_results = 0
        contractor_elements = body_content.find_all("article", class_="certification-card")
        logger.debug(f"Found {len(contractor_elements)} contractor elements.")
        contacts = []
        for element in contractor_elements:
            name_element = element.find("h2", class_="certification-card__heading")
            name = name_element.text.strip() if name_element else None
            details_url = element.find("h2", class_="certification-card__heading").find("a").get("href") if name_element else None
            phone_element = element.find("a", class_="certification-card__phone")
            phone = phone_element.get("href") if phone_element else None
            contacts.append({
                "type": "business",
                "industry": "roofing",
                "name": name,
                "phone": phone,
                "details_url": details_url
            })
        logger.info(f"Page {page_num} scraped. Extracted {len(contacts)} contacts.")
        logger.debug(f"Extracted contacts: {contacts}")
        return contacts
    except requests.RequestException as e:
        logger.error(f"Error scraping GAF: {e}")
        if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 403:
            logger.error("GAF is blocking our requests. Please try again later.")
        return []
    except Exception as e:
        logger.exception(f"An unexpected error occurred while scraping GAF: {e}")
        return []

def scrape_gaf_details(driver: webdriver.Chrome, url: str) -> Dict:
    logger.info(f"Scraping GAF details from URL: {url}")
    try:
        driver.get(url)
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                WebDriverWait(driver, 20, poll_frequency=1).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "image-masthead-carousel__info-wrapper"))
                )
                break
            except TimeoutException as e:
                if attempt == max_attempts:
                    logger.error(f"Timeout waiting for elements after {max_attempts} attempts.")
                    driver.quit()
                    return {}
                else:
                    logger.warning(f"Timeout waiting for elements (attempt {attempt}/{max_attempts}). Retrying...")
                    time.sleep(5)
                    driver.refresh()
        soup = BeautifulSoup(driver.page_source, "html.parser")
        body_content = soup.body
        logger.info(f"Got response from URL {url}")
        html_logger.debug(f"Response body: {body_content}")
        address_element = body_content.find("address", class_="image-masthead-carousel__address")
        address = address_element.text.strip() if address_element else None
        website_element = body_content.find("div", class_="image-masthead-carousel__links")
        website = website_element.find("a").get("href") if website_element and not website_element.find("a").get("href").__contains__("tel:") else None
        return {"address": address, "website": website}
    except requests.RequestException as e:
        logger.error(f"Error scraping GAF details: {e}")
        if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 403:
            logger.error("GAF is blocking our requests. Please try again later.")
        return {}
    except Exception as e:
        logger.exception(f"An unexpected error occurred while scraping GAF details: {e}")
        return {}

def extract_gaf_data(db: Session, location: dict, radius: int = 25, max_pages: int = -1) -> List[SourceData]:
    """Extracts data from GAF, handling pagination and setting geolocation based on zip code."""
    all_contacts = []
    driver = setup_driver()
    
    # Load zip code data
    zip_data = load_zip_code_data()
    
    # Set geolocation if zip code is provided
    if "zipCode" in location:
        zip_code = location["zipCode"]
        if zip_code in zip_data:
            lat, lon = zip_data[zip_code]
            driver.execute_cdp_cmd("Emulation.setGeolocationOverride", {
                "latitude": lat,
                "longitude": lon,
                "accuracy": 100
            })
            logger.info(f"Set geolocation to lat: {lat}, lon: {lon} for zip code: {zip_code}")
        else:
            logger.warning(f"Zip code {zip_code} not found in zip data.")
    else:
        logger.info("No zip code provided, not setting geolocation.")
    
    base_url = build_base_url(location, radius)

    logger.debug(f"Driver: {driver}")
    logger.debug(f"Base URL: {base_url}")
    logger.debug(f"DB: {db}")

    try:
        page_num = 1
        total_results = get_total_results(driver, base_url)

        if total_results == 0:
            logger.warning("No results found.")
            return []
        
        if max_pages == -1:
            max_pages = (total_results + 9) // 10

        logger.info(f"Found {total_results} results. Scraping up to {max_pages} pages.")

        while total_results > 0 and page_num <= max_pages:
            url = f"{base_url}#firstResult={10 * (page_num - 1)}"
            logger.debug(f"Scraping page {page_num} with URL: {url}")
            contacts = scrape_gaf(driver, url)
            if not contacts:
                logger.warning(f"No contacts found on page {page_num}.")
                break
            all_contacts.extend(contacts)
            page_num += 1

        for contact in all_contacts:
            logger.debug(f"Getting details for contact: {contact}")
            details_url = contact.get("details_url")
            if details_url:
                details = scrape_gaf_details(driver, details_url)
                logger.debug(f"Extracted details: {details}")
                contact.update(details)
        
    except Exception as e:
        logger.exception(f"An unexpected error occurred while extracting GAF data: {e}")
    
    if driver:
        driver.quit()

    source_url = get_top_level_url(base_url)
    source = SourceSchema(name="GAF", url=source_url)
    source_id = add_or_find_source(db, source)

    gaf_source_data = [SourceData(source_id=source_id, data=contact) for contact in all_contacts]
    logger.info(f"Extracted GAF data. Total contacts: {len(all_contacts)}")
    logger.debug(f"Extracted GAF data: {gaf_source_data}")
    return gaf_source_data

def export_to_csv(data: List[Business]) -> str:
    """Exports data to a CSV file."""
    filename = f"export_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    logger.debug(f"Exporting data to CSV: {filepath}")

    try:
        with open(filepath,
                mode='w',
                newline='') as file:
            writer = csv.DictWriter(file, fieldnames=data[0].keys())
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        logger.info(f"Data exported to CSV: {filename}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred while exporting data to CSV: {e}")
        return None
    return filename

processed1= ['19941', '19731', '81433', '80232', '80538', '81228', '81652', '81424', '81503', '80821', '80701', '81059', '80759', '81640', '80105', '81049', '81137', '80721', '81231', '80545', '81653', '81091', '80426', '81654', '80801', '80456', '80447', '81047', '80833', '81525', '80643', '81324', '80862', '81027', '80755', '81522', '81641', '81235', '81136', '80612', '81090', '81138', '81403', '81635', '80434', '80117', '81329', '80749', '80474', '80720', '81332', '81019', '80757', '81039', '81055', '81076', '80919', '81248', '81419', '81657', '81626', '81321', '81073', '81057', '81130', '80477', '80805', '81008', '81148', '80736', '81648', '80729', '81215', '80810', '81147', '81132', '81128', '80745', '81131', '81029', '81050', '81071', '81610', '81334', '80820', '80459', '81054', '80861', '81155', '80611', '81638', '80108', '81045', '81415', '65462', '63624', '65348', '65720', '64739', '64085', '64438', '63533', '63084', '65054', '65280', '64866', '63966', '65438', '64756', '64645', '63769', '63879', '63454', '64448', '64446', '65760', '63102', '65660', '65256', '63666', '63942', '65781', '63465', '65681', '64752', '64145', '65355', '64832', '65082', '64863', '63829', '63431', '65535', '65351', '64458', '63627', '63535', '63433', '64461', '65069', '64451', '63956', '65733', '65791', '63953', '64781', '65464', '64674', '65039', '65712', '65783', '65236', '63347', '63742', '64640', '63881', '63866', '65722', '64637', '71497', '70585', '70466', '71425', '71459', '70759', '71284', '70668', '70469', '71064', '71467', '70353', '70426', '71253', '71256', '70081', '70643', '71473', '70761', '71316', '71486', '71375', '70653', '70358', '70631', '70450', '71424', '70581', '71080', '70057', '70721', '71240', '70503', '71047', '70040', '70380', '70513', '71072', '70658', '70510', '71032', '71269', '71234', '70521', '70085', '70394', '97336', '97543', '97496', '97378', '97522', '97722', '97638', '97751', '97856', '97761', '97830', '97758', '97859', '97017', '97463', '97064', '97480', '97710', '97021', '97907', '97731', '97738', '97901', '97411', '97712', '97444', '97873', '97635', '97435', '97369', '97121', '97636', '97014', '97350', '97134', '97627', '97838', '97884', '97449', '97050', '97862', '97754', '97739', '97530', '97880', '97484', '97842', '97415', '97413', '97632', '97321', '97231', '97033', '97604', '97914', '97750', '97028', '97466', '97641', '97447', '97906', '97456', '97848', '97732', '97639', '97637', '97703', '97917', '97867', '97857', '97902', '97839', '97840', '97736', '97904', '97620', '97818', '97910', '97721', '97622', '97885', '97870', '97624', '97817', '97868', '58420', '58549', '58650', '58451', '58636', '58788', '58835', '58029', '58251', '58830', '58260', '58645', '58456', '58008', '58651', '58464', '58772', '58581', '58631', '58225', '58239', '58538', '58219', '58332', '58558', '58783', '58043', '58757', '58109', '58639', '58479', '58602', '58436', '58844', '58838', '58265', '58782', '58321', '58487', '58632', '58422', '58634', '58207', '58845', '58562', '58849', '58277', '58620', '58566', '58382', '58569', '58571', '58540', '58769', '58033', '58705', '58316', '58723', '58579', '58779', '58353', '58765', '58461', '58027', '58379', '22937', '23146', '24347', '23884', '23941', '24578', '22547', '22654', '24363', '24265', '23398', '24131', '24635', '23356', '23887', '24484', '24520', '24538']
processed2 = ['24076', '22577', '24603', '23457', '23438', '22980', '22733', '24092', '24270', '23089', '20175', '22830', '23511', '23894', '22243', '24413', '24069', '23040', '22724', '24361', '23091', '24136', '24563', '22743', '23694', '23227', '98544', '98616', '98930', '99347', '99326', '99017', '98848', '98256', '99185', '98831', '99167', '98833', '98575', '98619', '98305', '98940', '99153', '98641', '98248', '99121', '99128', '99356', '98362', '98612', '99155', '99402', '98832', '99346', '98660', '99156', '98548', '99349', '98535', '98852', '98639', '98826', '98297', '99122', '98533', '98266', '99163', '99337', '98557', '98946', '98851', '98859', '99109', '98903', '98397', '98283', '99217', '98855', '98384', '98292', '99362', '99371', '98812', '98391', '98827', '98361', '98620', '98024', '98325', '99329', '98267', '99169', '99115', '29129', '29692', '29554', '29551', '29906', '29676', '29322', '29547', '29055', '29566', '29831', '29439', '29899', '29001', '29442', '29703', '29709', '29922', '29126', '29643', '29435', '29545', '29458', '29836', '29661', '29530', '29038', '29061', '29353', '29469', '29432', '55318', '55784', '56628', '56279', '56438', '56207', '56592', '56458', '55732', '56444', '56666', '55923', '56673', '55771', '56547', '56654', '55803', '55603', '55385', '56143', '56522', '55066', '55604', '56728', '56655', '55919', '56029', '55051', '56371', '56341', '56711', '55796', '56219', '56257', '55977', '56630', '56548', '55713', '56481', '55981', '56623', '56668', '56027', '56591', '56364', '56069', '56260', '55616', '55725', '56553', '56658', '56676', '56722', '56167', '56636', '55615', '55766', '55971', '56474', '56215', '56685', '55783', '55924', '55362', '56055', '56294', '56528', '56759', '56147', '56142', '55082', '56721', '56725', '55084', '55072', '56714', '56744', '56175', '55798', '56042', '56727', '56056', '56567', '55371', '03244', '03215', '03589', '03839', '03755', '03451', '03076', '03771', '03592', '03813', '03249', '38359', '38069', '37308', '38544', '37877', '37733', '37066', '37659', '37043', '38126', '38080', '38488', '37680', '37851', '37380', '38251', '38575', '38067', '38572', '37753', '37765', '38365', '38041', '37882', '37028', '38577', '38257', '37405', '37305', '38006', '37179', '37078', '38358', '37026', '37934', '38486', '37333', '38483', '37352', '37846', '37187', '38363', '01039', '01752', '02346', '01952', '02633', '01258', '02535', '01521', '01267', '01475', '02055', '57534', '57560', '57553', '57652', '57469', '57766', '57762', '57047', '57235', '57752', '57620', '57471', '57532', '57312', '57633', '57247', '57538', '57745', '57758', '57563', '57645', '57030', '57216', '57735', '57370', '57626', '57457', '57322', '57750', '57574', '57260', '57650', '57340', '57642', '57737', '57770', '57625', '57576', '57724', '57361', '57799', '57439', '57438', '57572', '57528', '57381', '57780', '57223', '57775', '57346', '57375', '57761', '57054', '57433', '57776', '57632', '57040', '57010', '57276', '57552', '57520', '57034', '57537', '57420', '57345', '57315', '57231', '57479', '57719', '39747', '39078', '39348', '39046', '38754', '38966', '38668', '39561', '39661', '38829', '39736', '39461', '38647', '38844', '38769', '39572', '38644', '39153', '38731', '39669', '38965', '39322', '38680', '39063', '39457', '39150', '38847', '38917', '38652', '39735', '39355', '39212', '39403', '39365', '38877', '39156', '39649', '39352', '39562', '39483', '39341', '39109', '39194', '39479', '38916', '85629', '85550', '85141', '85634', '85553', '85337', '85933', '86322', '86052', '86332', '86337', '85610', '85548', '85940', '86503', '86004', '85360', '86047', '86514', '85321', '85613', '86022', '86445', '86040', '86436', '86432', '86435', '85633', '85605', '85926', '85173', '85333', '86504', '85324', '85942', '86323', '85627', '86535', '86024', '86444', '86021', '85936', '86031', '85354', '85655', '85621', '85341', '85172', '86439', '85632', '85911', '86510', '86035', '86434', '86036', '86016', '85735', '85530', '85541', '86556', '85643', '86305', '86505', '85263', '85545', '86033', '85348', '86411', '85631', '85042', '85356', '86039', '86054', '85342', '86512', '86045', '85334', '86046', '85920', '85350', '85344', '85534', '85328', '85357', '85533', '85359', '86018', '86044', '85623', '86443', '86406', '85352', '85191', '86053', '85323', '84740', '84720', '84027', '84199', '84537', '84532', '84734', '84511', '84718', '84525', '84733', '84329', '84533', '84751', '84536', '84034', '84008', '84728', '84083', '84539', '84784', '84055', '84714', '84635', '84730', '84515', '84313', '84510', '84535', '84029', '84522', '84741', '84629', '84531', '84018', '84637', '84775', '84336', '84051', '84759', '84035', '84529', '84540', '84649', '84080', '84340', '84066', '84663', '84038', '84716', '84046', '84316', '84320', '84023', '84022', '84086', '84639', '84315', '84052', '84726', '84643', '17271', '15423', '15548', '16027', '17876', '16677']
processed3 = ['19470', '17760', '18707', '17768', '16440', '16733', '18430', '18324', '15705', '18977', '16942', '16350', '17841', '15352', '16146', '18830', '19362', '17211', '19549', '17214', '15043', '15440', '16514', '16748', '19112', '18040', '15849', '16693', '17349']
processed4 = ['17726', '18628', '15673', '17057', '16254', '17266', '16301', '15860', '59522', '59643', '59762', '59486', '59640', '59825', '59864', '59916', '59053', '59013', '59075', '59345', '59004', '59327', '59059', '59344', '59322', '59255', '59538', '59523', '59338', '59223', '59410', '59077', '59520', '59211', '59463', '59079', '59025', '59020', '59411', '59820', '59010', '59353', '59758', '59542', '59722', '59446', '59736', '59241', '59930', '59854', '59925', '59759', '59416', '59324', '59421', '59525', '59027', '59318', '59841', '59326', '59844', '59062', '59008', '59826', '59039', '59544', '59645', '59448', '59725', '59545', '59858', '59427', '59201', '59089', '59312', '59086', '59016', '59441', '59635', '59066', '59073', '59336', '59333', '59057', '59915', '59422', '59524', '59337', '59501', '59064', '59868', '59420', '59720', '59772', '59452', '59546', '59074', '59259', '59923', '59240', '59871', '59927', '59830', '59724', '59011', '59084', '59221', '59317', '59311', '59466', '59489', '59215', '59276', '59343', '59928', '59262', '59535', '59319', '59212', '59260', '59935', '59078', '59873', '59052', '59747', '59351', '59739', '59339', '59872', '59263', '59827', '59316', '59214', '59087', '59430', '59710', '59527', '99641', '99667', '99650', '99572', '99743', '99705', '99758', '99774', '99777', '99565', '99557', '99675', '99757', '99575', '99748', '99768', '99665', '99722', '99746', '99745', '99720', '99566', '99764', '99776', '99737', '99732', '99730', '99721', '99724', '99505', '99679', '99691', '99791', '99761', '99781', '99788', '99674', '99749', '99754', '99657', '99578', '99789', '99727', '99628', '99615', '99833', '99925', '99753', '99689', '99784', '99603', '99581', '99820', '99690', '99649', '99540', '99826', '99740', '99755', '99734', '99738', '99610', '99549', '99574', '99678', '99684', '99929', '99682', '99772', '99762', '99653', '99782', '99759', '99583', '99835', '99659', '99747', '99612', '99630', '99736', '99622', '99692', '99923', '99723', '99752', '99769', '99750', '99767', '99602', '99661', '99783', '99546', '99836', '99547', '99733', '99766', '99620', '99638', '99608', '99693', '99668', '99652', '99632', '99729', '99927', '99742', '99770', '99664', '99655', '99553', '99786', '99648', '99771', '99625', '99731', '99643', '99756', '99922', '99841', '99830', '99741', '99903', '99714', '99579', '99739', '99569', '99621', '99666', '99647', '99607', '99556', '99555', '99680', '99763', '99716', '99627', '99663', '99635', '99571', '99585', '99918', '99780', '99765', '99688', '99726', '99515', '99658', '99550', '99672', '99640', '99580', '99773', '99588', '99676', '99827', '99651', '99801', '99785', '99686', '99548', '99563', '99950', '99744', '99613', '99832', '99644', '99614', '99558', '99706', '99662', '99586', '99840', '99590', '99926', '99606', '99564', '99677', '99573', '99825', '99589', '99751', '99636', '99824', '99778', '99697', '99760', '99561', '99633', '99683', '99708', '99821', '73838', '73501', '73047', '74533', '73435', '74849', '74501', '74722', '74941', '74445', '74452', '74001', '74602', '73851', '73650', '73901', '74333', '73728', '73544', '74738', '74740', '73949', '73668', '73842', '73565', '74837', '74960', '74022', '74947', '73759', '73063', '73646', '74652', '74540', '74865', '74747', '74370', '74112', '74469', '74963', '74338', '73015', '74559', '73562', '73022', '74531', '73942', '74031', '73664', '73150', '74023', '73735', '73933', '73542', '73448', '73011', '73932', '73638', '73843', '73947', '74045', '73539', '74079', '73031', '73853', '73041', '13740', '12927', '13835', '14717', '14507', '13220', '12586', '12222', '12997', '13626', '14001', '12957', '11709', '14858', '12503', '13664', '14642', '11959', '13814', '12764', '12979', '12861', '10307', '13436', '13317', '14590', '13618', '13749', '12873', '14736', '14708', '10979', '14126', '12563', '12480', '14882', '13302', '14047', '13694', '14892', '12923', '14437', '12879', '13783', '13435', '12878', '14772', '12134', '13313', '68959', '69027', '69042', '69143', '68879', '69350', '69190', '68766', '68422', '68666', '68042', '68655', '69347', '68739', '69211', '69346', '68061', '69128', '68977', '68803', '68776', '69162', '69351', '69358', '68850', '68719', '68970', '69030', '69044', '69218', '68375', '68431', '68001', '68005', '68637', '69157', '68781', '68343', '69365', '69170', '68309', '69026', '69167', '68760', '69121', '69212', '68640', '68711', '69217', '69123', '69169', '68852', '69221', '69334', '68933', '68768', '68759', '69152', '68856', '68379', '69127', '69339', '68753', '69348', '68345', '69168', '69163', '68859', '69336', '69161', '02816', '08037', '07802', '07710', '08070', '08556', '07647', '07827', '08008', '08102', '08252', '88031', '87036', '87538', '87832', '87820', '87357', '88254', '88136', '87012', '88213', '88118', '88422', '87577', '88318', '88265', '87528', '87740', '88415', '87523', '88121', '87821', '88112', '88081', '87006', '88113', '87749', '87070', '88410', '87829', '87746', '87419', '88252', '87654', '88419', '88029', '87825', '88301', '87724', '88264', '88056', '88039', '88063', '88250', '87052', '87512', '87520', '88262', '88321', '88134', '88135', '87824', '87747', '87827', '87011', '88122', '87539', '87035', '88435', '87735', '88344', '87124', '88348', '88004', '87930', '88028', '87007', '88202', '88431', '87347', '88040', '88426', '87420', '87018', '87320', '88263', '87943', '88023', '88337', '87327', '88045', '88439', '87418', '87037', '87364', '88201', '88268', '87034', '87053', '87939', '88342', '87313', '88343', '87401', '87013', '88033', '87750', '88330', '87315', '87060', '88055', '87040', '88401', '88352', '88338', '88034', '87531', '40048', '41465', '40475', '42544', '40827', '41010', '42038', '40145', '42070', '42444', '41121', '41513', '40077', '40730', '42223', '42135', '41074', '42602', '42351', '42758', '40434', '42049', '40843', '40383', '41267', '41034', '42047', '40104', '41425', '41722', '40484', '42337', '42127', '41081', '42140', '42201', '41128', '42746', '40350', '42344', '33459', '32820', '33859', '32669', '32013', '32430', '32030', '34251', '32570', '33332', '34141', '34473', '34992', '32055', '32328', '33708', '32445', '32046', '33043', '34102', '33435', '33921', '34756', '32541', '32403', '32169', '34498', '33852', '32345', '32080', '32568', '32567', '32035', '33149', '32631', '32348', '32053', '34674', '32963', '34773', '32346', '34267', '32040', '34973', '33972', '32180', '33524', '32427', '32343', '33030', '32937', '32628', '33034', '34739', '34206', '34142', '32182', '33538', '33860', '33440', '25180', '26422', '25159', '26270', '24991', '26761', '26180', '25699', '26525', '25419', '26038', '24732', '24873', '26050', '25550', '26802', '25507', '24941', '25840', '26146', '26238', '26750', '26541', '25183', '26638', '26291', '26601', '05826', '05762', '05360', '05902', '05081', '05460', '05731', '05089', '05906', '05461', '71903', '72843', '71852', '72721', '71659', '72108', '72466', '72658', '71839', '72443', '71653', '72379', '71725', '71749', '72358', '71937', '72059', '71836', '72733', '72127', '72578', '72478', '71921', '72342', '71676', '71861', '72629', '71677', '72170', '72011', '71772', '71965', '71631', '72078', '72534', '72373', '72624', '72761', '72916', '72851', '72630', '72479', '72301', '71747', '72955', '72938', '71764', '72581', '72842', '72402', '72567', '89403', '89418', '89310', '89316', '89833', '89118', '89426', '89834', '89314', '89427', '89826', '89822', '89424', '89883', '89404', '89046', '89311', '89419', '89003', '89825', '89832', '89830', '89409', '89034', '89496', '89061', '89421', '89029', '89508', '89317', '89821', '89415', '89019', '89005', '89425', '89013', '89420', '89405', '89022', '89315', '89823', '89820', '89021', '89001', '89018', '89042', '89010', '89445', '89444', '89017', '89449', '89049', '89020', '89835', '89025', '89045', '89008', '89438', '89043', '89023', '89422', '89318', '89319', '89047', '89085', '89803', '89412', '89446', '53018', '53593', '53962', '54469', '54138', '54773', '54749', '54819', '54527', '54890', '53809', '54408', '54558', '53949', '54853', '54437', '54228', '54844', '54143', '53512', '54121', '53158', '53541', '54246', '54021', '54880', '53070', '54534', '54756', '54981', '54643', '53594', '54727', '54463', '53821', '54840', '54850', '54862', '54554', '54235', '54411', '53577', '54020', '54156', '54856', '53195', '54841', '54545', '54434', '54979', '54107', '54513', '54632', '54629', '53092', '54344', '53035', '20639', '21610', '21521', '21795', '21629', '20687', '20662', '21088', '21842', '21766', '21060', '20882', '21856', '06813', '06079', '06243', '06379', '06615', '06074', '06498', '06059', '67801', '66772', '67042', '67658', '67880', '67871', '67733', '67757', '66079']
processed5 = ['35038', '36758', '35670', '36513', '35151', '35581', '36360', '35987', '36850', '35744', '36420', '36871', '36533', '35648', '36343', '36558', '35188', '36786', '35750', '35677', '36066', '36541', '35973', '36863', '36340', '35740', '36574', '35442', '35552', '36373', '35053', '35052', '36053', '35011', '35976', '36768', '36436', '35441', '36065', '35555', '36273', '36426', '36907', '36071', '36207', '36913', '36473', '36754', '35481', '36562', '36866', '95311', '95378', '95232', '95626', '94574', '95970', '95701', '95418', '95514', '96091', '92036', '91766', '91350', '93592', '93252', '93505', '93287', '93453', '93665', '92202', '92309', '95546', '93541', '96064', '95045', '92328', '96108', '93441', '96039', '92280', '95428', '92239', '96134', '93001', '92285', '92058', '92301', '92363', '93428', '96123', '94512', '95450', '92173', '95532', '94924', '93255', '90275', '96057', '95536', '95386', '91934', '95488', '93512', '93243', '96041', '93653', '93922', '95423', '96021', '96110', '95364', '95918', '92310', '95459', '93434', '93031', '95227']
processed_zips = processed1 + processed2 + processed3 + processed4 + processed5

if __name__ == "__main__":
    count = {'new': 0, 'existing': 0}
    from dependencies import get_db_conn
    from models import CoverageZipList
    print("Running service directly...")
    zip_codes = []

    db = next(get_db_conn())

    logger.info("Extracting areas from db...")
    zip_codes = get_zips_to_search_by_states(db, ['Georgia'], 25)
    
    logger.info(f"Extracted ZIP codes: {zip_codes}")
    for zip_code in zip_codes:
        if zip_code not in processed_zips:
            logger.debug(f"Extracting data for ZIP code: {zip_code} ({len(zip_codes) - zip_codes.index(zip_code)} remaining)")
            businesses = extract_gaf_data(db, {"zipCode": zip_code}, 25)
            for business in businesses:
                logger.info(f"Adding business: {business}")
                result = insert_company_data(db, business)
                if result["existing"]:
                    count["existing"] += 1
                else:
                    count["new"] += 1
            logger.info(f"New businesses: {count['new']}, Existing businesses: {count['existing']}")
        elif zip_code in processed_zips:
            logger.debug(f"ZIP code {zip_code} already processed. Skipping...")
            logger.debug(f"{len(zip_codes) - zip_codes.index(zip_code)} remaining.")
    print("Service run complete.")