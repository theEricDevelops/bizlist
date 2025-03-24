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
    

processed_zips = ['19941', '19731', '81433', '80232', '80538', '81228', '81652', '81424', '81503', '80821', '80701', '81059', '80759', '81640', '80105', '81049', '81137', '80721', '81231', '80545', '81653', '81091', '80426', '81654', '80801', '80456', '80447', '81047', '80833', '81525', '80643', '81324', '80862', '81027', '80755', '81522', '81641', '81235', '81136', '80612', '81090', '81138', '81403', '81635', '80434', '80117', '81329', '80749', '80474', '80720', '81332', '81019', '80757', '81039', '81055', '81076', '80919', '81248', '81419', '81657', '81626', '81321', '81073', '81057', '81130', '80477', '80805', '81008', '81148', '80736', '81648', '80729', '81215', '80810', '81147', '81132', '81128', '80745', '81131', '81029', '81050', '81071', '81610', '81334', '80820', '80459', '81054', '80861', '81155', '80611', '81638', '80108', '81045', '81415', '65462', '63624', '65348', '65720', '64739', '64085', '64438', '63533', '63084', '65054', '65280', '64866', '63966', '65438', '64756', '64645', '63769', '63879', '63454', '64448', '64446', '65760', '63102', '65660', '65256', '63666', '63942', '65781', '63465', '65681', '64752', '64145', '65355', '64832', '65082', '64863', '63829', '63431', '65535', '65351', '64458', '63627', '63535', '63433', '64461', '65069', '64451', '63956', '65733', '65791', '63953', '64781', '65464', '64674', '65039', '65712', '65783', '65236', '63347', '63742', '64640', '63881', '63866', '65722', '64637', '71497', '70585', '70466', '71425', '71459', '70759', '71284', '70668', '70469', '71064', '71467', '70353', '70426', '71253', '71256', '70081', '70643', '71473', '70761', '71316', '71486', '71375', '70653', '70358', '70631', '70450', '71424', '70581', '71080', '70057', '70721', '71240', '70503', '71047', '70040', '70380', '70513', '71072', '70658', '70510', '71032', '71269', '71234', '70521', '70085', '70394', '97336', '97543', '97496', '97378', '97522', '97722', '97638', '97751', '97856', '97761', '97830', '97758', '97859', '97017', '97463', '97064', '97480', '97710', '97021', '97907', '97731', '97738', '97901', '97411', '97712', '97444', '97873', '97635', '97435', '97369', '97121', '97636', '97014', '97350', '97134', '97627', '97838', '97884', '97449', '97050', '97862', '97754', '97739', '97530', '97880', '97484', '97842', '97415', '97413', '97632', '97321', '97231', '97033', '97604', '97914', '97750', '97028', '97466', '97641', '97447', '97906', '97456', '97848', '97732', '97639', '97637', '97703', '97917', '97867', '97857', '97902', '97839', '97840', '97736', '97904', '97620', '97818', '97910', '97721', '97622', '97885', '97870', '97624', '97817', '97868', '58420', '58549', '58650', '58451', '58636', '58788', '58835', '58029', '58251', '58830', '58260', '58645', '58456', '58008', '58651', '58464', '58772', '58581', '58631', '58225', '58239', '58538', '58219', '58332', '58558', '58783', '58043', '58757', '58109', '58639', '58479', '58602', '58436', '58844', '58838', '58265', '58782', '58321', '58487', '58632', '58422', '58634', '58207', '58845', '58562', '58849', '58277', '58620', '58566', '58382', '58569', '58571', '58540', '58769', '58033', '58705', '58316', '58723', '58579', '58779', '58353', '58765', '58461', '58027', '58379', '22937', '23146', '24347', '23884', '23941', '24578', '22547', '22654', '24363', '24265', '23398', '24131', '24635', '23356', '23887', '24484', '24520', '24538']

if __name__ == "__main__":
    count = {'new': 0, 'existing': 0}
    from dependencies import get_db_conn
    from models import CoverageZipList
    print("Running service directly...")
    zip_codes = []

    db = next(get_db_conn())

    logger.info("Extracting areas from db...")
    all_params = db.execute(select(CoverageZipList.params).distinct()).scalars().all()
    states = []
    for param in all_params:
        try:
            states.append(eval(param)["area"])
        except Exception as e:
            logger.error(f"Error parsing area: {e}")

    for state in states:
        logger.debug(f"Extracting ZIP codes for state: {state}")
        state_zips = db.query(CoverageZipList).filter(CoverageZipList.params.like(f'%area\': \'{state}\'%')).all()
        for zip_entry in state_zips:
            zip_codes.extend(zip_entry.zips.split(','))
    
    logger.info(f"Extracted ZIP codes: {zip_codes}")
    for zip_code in zip_codes:
        if zip_code not in processed_zips:
            logger.debug(f"Extracting data for ZIP code: {zip_code}")
            businesses = extract_gaf_data(db, {"zipCode": zip_code}, 25)
            for business in businesses:
                logger.debug(f"Adding business: {business}")
                result = insert_company_data(db, business)
                if result["existing"]:
                    count["existing"] += 1
                else:
                    count["new"] += 1
            logger.info(f"New businesses: {count['new']}, Existing businesses: {count['existing']}")
    print("Service run complete.")