from app.services.logger import Logger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from sqlalchemy.orm import Session
from bs4 import BeautifulSoup
from typing import List, Dict
import time
import requests

from app.services.source import add_or_find_source
from app.services.scraping import ScrapingService
from app.schemas.source import SourceData, SourceSchema

log = Logger('scraper-gaf', log_level='INFO')
html_log = Logger('scraper-gaf-html')

class GAFScraper:
    """
    Scraper for GAF contractors.
    """
    def __init__(self, location: dict, radius: int, db: Session = None, source: SourceSchema = None):
        log.debug("Initializing GAF source.")
        self.location = location
        self.radius = radius
        self.db = db
        self.source = source if source else add_or_find_source(db, SourceSchema(name="GAF", url="https://www.gaf.com/en-us/roofing-contractors/residential"))
        log.debug(f"Source: {self.source}")
        self.scraper = ScrapingService()

    def _get_listings_from_page(self, driver: webdriver.Chrome, url: str, page_num: int = 1) -> List[Dict]:
        if page_num > 1:
            url += f"#firstResult={10 * (page_num - 1)}"
        try:
            log.info(f"Scraping GAF with URL: {url}")
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
                        log.error(f"Timeout waiting for elements after {max_attempts} attempts.")
                        driver.quit()
                        return []
                    else:
                        log.warning(f"Timeout waiting for elements (attempt {attempt}/{max_attempts}). Retrying...")
                        time.sleep(5)
                        driver.refresh()
            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")
            body_content = soup.body
            html_log.debug(f"Response body: {body_content}")
            query_summary = body_content.find("div", class_="query-summary")
            if query_summary:
                total_results_str = query_summary.text.strip().split("of ")[1].split(" ")[0]
                try:
                    total_results = int(total_results_str)
                    log.info(f"Total results: {total_results}")
                except (ValueError, IndexError):
                    log.warning("Could not extract total results.")
                    total_results = 0
            else:
                log.warning("Could not find query summary.")
                total_results = 0
            contractor_elements = body_content.find_all("article", class_="certification-card")
            log.debug(f"Found {len(contractor_elements)} contractor elements.")
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
            log.info(f"Page {page_num} scraped. Extracted {len(contacts)} contacts.")
            log.debug(f"Extracted contacts: {contacts}")
            return contacts
        except requests.RequestException as e:
            log.error(f"Error scraping GAF: {e}")
            if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 403:
                log.error("GAF is blocking our requests. Please try again later.")
            return []
        except Exception as e:
            log.exception(f"An unexpected error occurred while scraping GAF: {e}")
            return []

    def _get_details_from_url(self, driver: webdriver.Chrome, url: str) -> Dict:
        log.info(f"Scraping GAF details from URL: {url}")
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
                        log.error(f"Timeout waiting for elements after {max_attempts} attempts.")
                        driver.quit()
                        return {}
                    else:
                        log.warning(f"Timeout waiting for elements (attempt {attempt}/{max_attempts}). Retrying...")
                        time.sleep(5)
                        driver.refresh()
            soup = BeautifulSoup(driver.page_source, "html.parser")
            body_content = soup.body
            log.info(f"Got response from URL {url}")
            html_log.debug(f"Response body: {body_content}")
            address_element = body_content.find("address", class_="image-masthead-carousel__address")
            address = address_element.text.strip() if address_element else None
            website_element = body_content.find("div", class_="image-masthead-carousel__links")
            website = website_element.find("a").get("href") if website_element and not website_element.find("a").get("href").__contains__("tel:") else None
            return {"address": address, "website": website}
        except requests.RequestException as e:
            log.error(f"Error scraping GAF details: {e}")
            if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 403:
                log.error("GAF is blocking our requests. Please try again later.")
            return {}
        except Exception as e:
            log.exception(f"An unexpected error occurred while scraping GAF details: {e}")
            return {}
        
    def _get_total_results_from_url(driver: webdriver.Chrome, url: str) -> int:
        try:
            log.info(f"Getting total results from URL: {url}")
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
                        log.error(f"Timeout waiting for elements after {max_attempts} attempts.")
                        driver.quit()
                        return 0
                    else:
                        log.warning(f"Timeout waiting for elements (attempt {attempt}/{max_attempts}). Retrying url {url}...")
                        time.sleep(5)
                        driver.refresh()
            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")
            body_content = soup.body
            html_log.debug(f"Response body: {body_content}")
            query_summary = body_content.find("div", class_="query-summary")
            if query_summary:
                total_results_str = query_summary.text.strip().split("of ")[1].split(" ")[0]
                try:
                    total_results = int(total_results_str)
                    log.info(f"Total results: {total_results}")
                    return total_results
                except (ValueError, IndexError):
                    log.warning("Could not extract total results.")
                    return 0
            elif body_content.find("div", class_="error-message"):
                log.warning("No results found.")
                return 0
            else:
                log.warning("Could not find query summary.")
                return 0
        except requests.RequestException as e:
            log.error(f"Error getting total results: {e}")
            if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 403:
                log.error("GAF is blocking our requests. Please try again later.")
            return 0
        except Exception as e:
            log.exception(f"An unexpected error occurred while getting total results: {e}")
            return 0
        
    def _get_all_listings(self, db: Session, location: dict, radius: int = 25, max_pages: int = -1) -> List[SourceData]:
        """Extracts data from GAF, handling pagination and setting geolocation based on zip code."""
        all_contacts = []
        driver = self.scraper.setup_driver()
        
        self.scraper.set_geolocation(driver, location)
        
        base_url = self.scraper.build_base_url(location, radius)

        log.debug(f"Driver: {driver}")
        log.debug(f"Base URL: {base_url}")
        log.debug(f"DB: {db}")

        try:
            page_num = 1
            total_results = self._get_total_results_from_url(driver, base_url)

            if total_results == 0:
                log.warning("No results found.")
                return []
            
            if max_pages == -1:
                max_pages = (total_results + 9) // 10

            log.info(f"Found {total_results} results. Scraping up to {max_pages} pages.")

            while total_results > 0 and page_num <= max_pages:
                url = f"{base_url}#firstResult={10 * (page_num - 1)}"
                log.debug(f"Scraping page {page_num} with URL: {url}")
                contacts = self.get_listings_from_page(driver, url)
                if not contacts:
                    log.warning(f"No contacts found on page {page_num}.")
                    break
                all_contacts.extend(contacts)
                page_num += 1

            for contact in all_contacts:
                log.debug(f"Getting details for contact: {contact}")
                details_url = contact.get("details_url")
                if details_url:
                    details = self.get_details(driver, details_url)
                    log.debug(f"Extracted details: {details}")
                    contact.update(details)
            
        except Exception as e:
            log.exception(f"An unexpected error occurred while extracting GAF data: {e}")
        
        if driver:
            driver.quit()

        gaf_source_data = [SourceData(source_id=self.source.id, data=contact) for contact in all_contacts]
        log.info(f"Extracted GAF data. Total contacts: {len(all_contacts)}")
        log.debug(f"Extracted GAF data: {gaf_source_data}")
        return gaf_source_data
    