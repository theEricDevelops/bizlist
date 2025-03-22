import os
import requests
from bs4 import BeautifulSoup
from schemas import SourceData, SourceSchema
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from models import Business, Contact, BusinessContact
from openai import OpenAI

import re
import logging
import json

# Configure logging
# Convert the log folder from a relative path to an absolute path. The user has specified a path
# relative to the root of the project, so we need to convert it to an absolute path.
log_folder = os.getenv("LOG_FOLDER", "/logs") # Default to /logs if LOG_FOLDER is not set
log_folder = os.path.abspath(log_folder)
log_file = os.path.join(log_folder, os.getenv("LOG_FILE", "bizlist.log"))
log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
os.makedirs(log_folder, exist_ok=True)
log_level = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(
    filename=log_file,
    level=log_level,
    format=log_format
)

logger = logging.getLogger(__name__)

def get_html_from_url(url: str) -> str:
    """
    Retrieves HTML content from a URL.

    Args:
        url (str): URL to retrieve HTML content from.

    Returns:
        str: HTML content.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    try:
        logger.info(f"Retrieving HTML from URL: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        soup = BeautifulSoup(response.content, "html.parser")
        body_content = str(soup.body)

        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response content: {response.content}")
        logger.debug(f"Response headers: {response.headers}")
                
        return body_content
    except requests.RequestException as e:
        logger.error(f"Error retrieving HTML from URL: {url}")
        logger.error(e)
        return None
    except Exception as e:
        logger.exception(f"An unexpected error occurred while retrieving HTML from URL: {url}")
        return None

def send_html_to_llm_for_extraction(html: str, expected: List[str]) -> Dict:
    """
    Sends HTML to AI and returns extracted elements.

    Args:
        html (str): HTML content to send to AI for extraction.
        expected (List[str]): Expected elements to extract from the HTML.

    Returns:
        dict: Extracted elements.
    """

    system_message = """
        You are a web scraping expert.  Analyze the following HTML from a search results page.

        For each result, extract:

        * Company Name
        * Phone Number
        * URL of the details page for the company

        Return the data as a JSON array of objects, where each object has the keys "company", "phone", and "details_url".  If a field is missing, use "null".
        Example:
        {
            "companies": [ 
                {
                    "company": "AI Roofing",
                    "phone": "1234567890",
                    "details_url": "https://www.airoofing.com"
                },
                {
                    "company": "AI Roofing 2",
                    "phone": "1234567890",
                    "details_url": "https://www.airoofing2.com"
                }
            ]
        }
    """

    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        raise ValueError("XAI_API_KEY environment variable not set.")
        return None
    
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.x.ai/v1",
    )

    logger.info("Sending HTML to AI for extraction")
    logger.debug(f"HTML: {html}")
    logger.debug(f"Expected elements: {expected}")
    completion = client.chat.completions.create(
        model="grok-2-latest",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": html},
        ],
    )

    logger.debug(f"AI response: {completion}")

    print(completion.choices[0].message.content)
    # Mock AI response
    return {
        "companies": [ 
            {
                "company": "AI Roofing",
                "phone": "1234567890",
                "details_url": "https://www.airoofing.com"
            },
            {
                "company": "AI Roofing 2",
                "phone": "1234567890",
                "details_url": "https://www.airoofing2.com"
            }
        ]
    }

def insert_data(db: Session, source_data: List[SourceData]):
    """Inserts business and contact data into the database, handling missing fields."""
    for item in source_data:
        source_id = item.source_id
        data = item.data

        # Find or create business
        business_name = data.get("company")
        business = db.execute(select(Business).where(Business.name == business_name)).scalar()
        if not business:
            business = Business(name=business_name)
            db.add(business)
            db.flush()

        # Find or create contact
        contact_name = data.get("name")
        contact = db.execute(select(Contact).where(func.lower(Contact.first_name) == func.lower(contact_name))).scalar() #Case-insensitive search
        if not contact:
            contact = Contact(first_name=data.get("name", ""), last_name="", email=data.get("email"), phone=data.get("phone"), title="")
            db.add(contact)
            db.flush()

        # Add business-contact association (if business exists)
        if business:
            business_contact = db.execute(select(BusinessContact).where(BusinessContact.business_id == business.id, BusinessContact.contact_id == contact.id)).scalar()
            if not business_contact:
                business_contact = BusinessContact(business_id=business.id, contact_id=contact.id)
                db.add(business_contact)

    db.commit()
    print("Data inserted successfully!")

def scrape_gaf(location: dict, radius: int = 25, page_num: int = 1) -> List[Dict]:
    """
    Scrapes contractor data from GAF's website.
    
    Args:
        location (dict): Location data containing "state" and "city" or a ZIP code.
        radius (int): Search radius in miles.
        page_num (int): Page number to scrape.

    Returns:
        List[Dict]: List of contractor data.
    """

    if "state" in location and "city" in location:
        url = f"https://www.gaf.com/en-us/roofing-contractors/residential/usa/{location['state']}/{location['city']}?distance={radius}"
    elif "zipCode" in location:
        url=f"https://www.gaf.com/en-us/roofing-contractors/residential?postalCode={location['zipCode']}&distance={radius}&countryCode=us"
    elif ("state" in location and not "city" in location) or ("city" in location and not "state" in location):
        raise ValueError("Both 'state' and 'city' are required if one is provided.")
    elif ("state" in location or "city" in location) and "zip" in location:
        raise ValueError("You need to provide either 'state' and 'city' or 'zip', not both.")
    else:
        raise ValueError("You need to provide either 'state' and 'city' or 'zip'.")
    
    if page_num > 1:
        url += f"#firstResult={10 * (page_num - 1)}"

    try:
        logger.info(f"Scraping GAF with URL: {url}")

        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        soup = BeautifulSoup(response.content, "html.parser")

        contractor_elements = soup.find_all("article", class_="certification-card")

        contacts = []
        for element in contractor_elements:
            name_element = element.find("h2", class_="certification-card__heading")
            if name_element:
                name = name_element.text.strip()
            else:
                name = None

            details_url_element = element.find("h2", class_="certification-card__heading").find("a").get("href")
            if details_url_element:
                details_url = details_url_element.
            else:
                details_url = None

            phone_element = element.find("a", class_="contractor-phone")
            if phone_element:
                phone = phone_element.text.strip()
            else:
                phone = None

            address_element = element.find("p", class_="contractor-address")
            if address_element:
                address = address_element.text.strip()
            else:
                address = None

            website_element = element.find("a", class_="contractor-website")
            if website_element:
                website = website_element.get("href").strip()
            else:
                website = None

            contacts.append({
                "name": name,
                "phone": phone,
                "address": address,
                "website": website
            })

        return contacts

def extract_gaf_data(postal_code: str, radius: int = 25, max_pages: int = 10) -> List[SourceData]:
    """Extracts data from GAF, handling pagination."""
    all_contacts = []
    page_num = 1
    while True:
        contacts = scrape_gaf(postal_code, radius, page_num)
        if not contacts:
            break #No more contacts found
        all_contacts.extend(contacts)
        page_num += 1
        if page_num > max_pages:
            break #Reached max pages

    # Assuming you have a source with id 3 for GAF
    gaf_source_data = [SourceData(source_id=3, data=contact) for contact in all_contacts]
    return gaf_source_data

if __name__ == "__main__":
    send_html_to_llm_for_extraction(get_html_from_url('https://www.gaf.com/en-us/roofing-contractors/residential/usa/ga/canton?distance=25'), ["companies"])