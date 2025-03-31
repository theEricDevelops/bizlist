import re
from app.services.logger import Logger
from typing import Tuple

log = Logger('service-formatter')

class Formatter:
    def __init__(self):
        self.log = log

    def name(self, name: str) -> str:
        """Format a company name by removing extra space and capitalizing each word
        while treating 'and' and 'the' as lowercase and keeping acronyms capitalized."""
        log.debug(f"Formatting name: {name}")
        if not name:
            log.debug(f"No name found")
            return None
        name = re.sub(r'\s+', ' ', name.strip())
        name = re.sub(r'(?<!\w)(and|the)(?!\w)', lambda m: m.group(0).lower(), name, flags=re.IGNORECASE)
        name = re.sub(r'\b[A-Z]{2,}\b', lambda m: m.group(0).upper(), name)
        # Remove LLC, Inc., Corp., etc. from the end of the name
        name = re.sub(r'\s+(LLC|Inc\.|Corp\.|Ltd\.|Pty\.|GmbH|S\.A\.R\.L)\b', '', name, flags=re.IGNORECASE)
        # Remove any trailing commas or periods
        name = re.sub(r'[,.]+$', '', name)
        # Remove any leading or trailing whitespace
        name = name.strip()
        # Capitalize each word
        name = re.sub(r'\s+', ' ', name)  # Normalize spaces
        
        formatted_name = ' '.join(word.capitalize() for word in name.split())
        log.debug(f"Formatted name: {formatted_name}")
        return formatted_name

    def phone(self, number: str) -> str:
        """Format a phone number by removing non-numeric characters and returning the last 10 digits."""
        number = number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace(".", "").replace("+", "")
        number = number.split("tel:")[-1] if number.startswith("tel:") else number
        if len(number) == 10:
            log.debug(f"Returning phone number: {number}")
            return number
        elif len(number) == 11 and number[0] == "1":
            log.debug(f"Formatting phone number: {number}")
            return number[1:]
        else:
            log.warning(f"Invalid phone number: {number}")
            return None

    def zip(self, zip_code: str) -> str:
        """Format a ZIP code by removing non-numeric characters and returning the last 5 or 9 digits."""
        zip_code = zip_code.replace("-", "").replace(" ", "")
        if (len(zip_code) == 5 or len(zip_code) == 9) and zip_code.isdigit():
            log.debug(f"Returning ZIP code: {zip_code}")
            return zip_code
        else:
            log.warning(f"Invalid ZIP code: {zip_code}")
            return None

    def website(self, website: str) -> str:
        """Format a website URL by ensuring it starts with 'http://' or 'https://'."""
        if not website:
            log.debug(f"No website found")
            return None
        website = website.strip()
        url_pattern = r"^(?:http(s)?:\/\/)?[\w.-]+(?:\.[\w\.-]+)+[\w\-\._~:/?#[\]@!\$&'\(\)\*\+,;=.]+$"
        match = re.match(url_pattern, website, re.IGNORECASE)
        if match:
            if not website.startswith("http"):
                website = f"https://{website}"
            log.debug(f"Returning website: {website}")
            return website
        elif match is None:
            log.debug(f"No website found")
            return None
        else:
            log.warning(f"Invalid website: {website}")
            return None

    def email(self, email: str) -> str:
        """Format an email address by ensuring it follows a standard format."""
        if not email:
            log.debug(f"No email found")
            return None
        email = email.strip()
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        match = re.match(email_pattern, email)
        if match:
            log.debug(f"Returning email: {email}")
            return email
        else:
            log.warning(f"Invalid email: {email}")
            return None
    
    def address_parts(self, address_str: str) -> Tuple[str, str, str, str, str]:
        """Parse an address string into its components: address1, address2, city, state, and zip code."""
        log.debug(f"Parsing address: {address_str}")
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
        log.debug(f"Extracted address parts: {address1}, {address2}, {city}, {state}, {zip_code}")
        return (address1, address2, city, state, zip_code)