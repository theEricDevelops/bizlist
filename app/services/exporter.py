import csv
import os
import re
from datetime import datetime
from typing import List
from app.core.config import config
from app.services.logger import Logger

from app.models.contact import Business
from app.schemas.contact import BusinessSchema

from app.services.formatter import Formatter

log = Logger('service-exporter')


class Exporter:
    def __init__ (self):
        pass

    def to_csv(self, data: List[Business], fieldnames: List[str], filename: str = None) -> str:
        """Exports data to a CSV file."""
        log.info(f"Exporting data to CSV: {filename}")
        if filename:
            # Verify the filename passed by the user is safe
            if not filename.isalnum() and not filename.replace('_', '').isalnum():
                log.error("Invalid filename provided. Only alphanumeric characters and underscores are allowed.")

            # If the filename has an extension, remove it
            match = re.match(r'^(.*?)(\.[^.]*$|$)', filename)
            if match:
                filename = match.group(1)
        else:
            # Generate a default filename if none is provided
            filename = "export"

        # Append a timestamp to the filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        filename = f"{filename}_{timestamp}.csv"
                    
        filepath = os.path.join(config.download_dir, filename)
        log.debug(f"Exporting data to CSV: {filepath}")

        try:
            # Ensure the download directory exists
            os.makedirs(config.download_dir, exist_ok=True)
            # Write data to CSV file
            log.info(f"Writing data to CSV file: {filepath}")
            
            # Create formatter instance
            formatter = Formatter()
            
            with open(filepath,
                    mode='w',
                    newline='') as file:
                
                # Convert model instances to dictionaries and clean them
                rows = []
                for item in data:
                    # Filter out SQLAlchemy internal attributes
                    row_dict = {k: v for k, v in item.__dict__.items() 
                               if not k.startswith('_sa_')
                               and not k.startswith('id')
                               and k != 'notes'}  
                    
                    # Format individual fields if needed
                    if 'name' in row_dict:
                        log.debug(f"Formatting name: {str(row_dict['name'])}")
                        row_dict['name'] = formatter.name(str(row_dict['name']))
                    if 'phone' in row_dict:
                        log.debug(f"Formatting phone: {row_dict['phone']}")
                        row_dict['phone'] = formatter.phone(str(row_dict['phone']))
                    if 'address' in row_dict:
                        log.debug(f"Formatting address: {row_dict['address']}")
                        row_dict['address'] = formatter.name(str(row_dict['address']))
                    if 'address2' in row_dict:
                        log.debug(f"Formatting address2: {row_dict['address2']}")
                        row_dict['address2'] = formatter.name(str(row_dict['address2']))
                    if 'city' in row_dict:
                        log.debug(f"Formatting city: {row_dict['city']}")
                        row_dict['city'] = formatter.name(str(row_dict['city']))
                    if 'zip' in row_dict:
                        log.debug(f"Formatting zip: {row_dict['zip']}")
                        row_dict['zip'] = formatter.zip(str(row_dict['zip']))
                    if 'website' in row_dict:
                        log.debug(f"Formatting website: {row_dict['website']}")
                        row_dict['website'] = formatter.website(str(row_dict['website']))
                    if 'industry' in row_dict:
                        log.debug(f"Formatting industry: {row_dict['industry']}")
                        row_dict['industry'] = formatter.name(str(row_dict['industry']))
                    
                    rows.append(row_dict)
                
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
            log.info(f"Data exported to CSV: {filename}")
        except Exception as e:
            log.error(f"An unexpected error occurred while exporting data to CSV: {e}")
            return None
        return filename