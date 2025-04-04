from typing import Optional
from app.services.logger import Logger
from app.core.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import Depends
from sqlalchemy import func

from app.models.location import ZipCode

log = Logger('service-location', log_level='DEBUG')

class LocationService:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        self.location = None
        pass
    
    def _get_location_by_zip(self, zip_code: str | int) -> Optional[ZipCode]:
        """
        Retrieve a location by its zip code.
        """
        zip_code = str(zip_code)
        zip_code_object = self.db.query(ZipCode).filter(ZipCode.zip == zip_code).first()
        if zip_code_object:
            return zip_code_object
        log.warning(f"Location not found for zip: {zip}")
        return None
    
    def _get_location_by_city(self, city: str, state: str) -> Optional[ZipCode]:
        """
        Retrieve a location by its city name.
        """
        try:
            zip_code_object = self.db.query(ZipCode).filter(func.lower(ZipCode.city) == city.lower(), func.lower(ZipCode.state) == state.lower()).first()
            if zip_code_object:
                return zip_code_object
            log.warning(f"Location not found for city: {city}, state: {state}")
            return None
        except SQLAlchemyError as e:
            log.error(f"Database error: {e}")
            return None
        except Exception as e:
            log.error(f"Unexpected error: {e}")
            return None
    
    def _get_attribute(self, zip_code_object: ZipCode, attribute: str) -> Optional[str]:
        """
        Retrieve a specific attribute (e.g., zip code, city, state) from the location.
        """
        if hasattr(zip_code_object, attribute):
            return getattr(zip_code_object, attribute)
        log.warning(f"Attribute '{attribute}' not found in location object.")
        return None
    
    def add(self, location: ZipCode) -> ZipCode:
        """
        Add a new location to the database.
        """
        try:
            self.db.add(location)
            self.db.commit()
            self.db.refresh(location)
            log.info(f"Location added: {location}")
            return location
        except SQLAlchemyError as e:
            log.error(f"Error adding location: {e}")
            self.db.rollback()
            raise
        except Exception as e:
            log.error(f"Unexpected error: {e}")
            self.db.rollback()
            raise
    
    def get(self, location: str | int, attribute: str = None) -> Optional[ZipCode]:
        """
        Retrieve a location based on the provided identifier (ID, zip code, or city).
        """
        zip_code_object = None
        try:
            if (isinstance(location, str) and location.isdigit()) or (isinstance(location, int) and len(str(location)) == 5):
                # Assuming it's a zip code
                zip_code_object = self._get_location_by_zip(location)
            elif isinstance(location, str) and ',' in location:
                # Assuming it's a city and state combination (e.g., "Nashville,TN")
                city, state = location.split(',', 1)
                city = city.strip(",").strip()
                state = state.strip()

                if not city or not state:
                    log.error(f"Invalid location format: {location}")
                    raise ValueError("Invalid location format. Expected 'city,state'.")
                
                zip_code_object = self._get_location_by_city(city, state)
            else:
                log.error(f"Invalid location format: {location}")
                raise ValueError("Invalid location format. Expected zip code or 'city,state'.")
            
            if zip_code_object and attribute:
                # If an attribute is specified, return the specific attribute value
                return self._get_attribute(zip_code_object, attribute)
            
            return zip_code_object
        except AttributeError as e:
            log.error(f"Attribute error: {e}")
            return None
        except TypeError as e:
            log.error(f"Type error: {e}")
            return None
        except IndexError as e:
            log.error(f"Index error: {e}")
            return None
        except KeyError as e:
            log.error(f"Key error: {e}")
            return None
        except ValueError:
            log.error(f"Invalid location format: {location}")
            return None
        except SQLAlchemyError as e:
            log.error(f"Database error: {e}")
            return None
        except Exception as e:
            log.error(f"Unexpected error: {e}")
            return None
    
    def update(self, location: str | int, **kwargs) -> Optional[ZipCode]:
        """
        Update a location based on the provided identifier (zip code or city/state).
        """
        zip_code_object = self.get(location)
        if not zip_code_object:
            log.warning(f"Location not found for update: {location}")
            return None
        
        try:
            for key, value in kwargs.items():
                setattr(zip_code_object, key, value)
            self.db.commit()
            return zip_code_object
        except AttributeError as e:
            log.error(f"Attribute error: {e}")
            self.db.rollback()
            return None
        except SQLAlchemyError as e:
            log.error(f"Error updating location: {e}")
            self.db.rollback()
            return None
        except Exception as e:
            log.error(f"Unexpected error: {e}")
            self.db.rollback()
            return None
    
    def delete(self, location: str | int) -> bool:
        """
        Delete a location based on the provided identifier (zip code or city/state).
        """
        zip_code_object = self.get(location)
        if not zip_code_object:
            log.warning(f"Location not found for deletion: {location}")
            return False
        
        try:
            self.db.delete(zip_code_object)
            self.db.commit()
            log.info(f"Location deleted: {zip_code_object}")
            return True
        except SQLAlchemyError as e:
            log.error(f"Error deleting location: {e}")
            self.db.rollback()
            return False
        except Exception as e:
            log.error(f"Unexpected error: {e}")
            self.db.rollback()
            return False
    
    def get_cid(self, location: str | int) -> Optional[str]:
        """
        Retrieve the Google CID for a location based on the provided identifier (zip code or city/state).
        """
        zip_code_object = self.get(location, 'google_cid')
        if not zip_code_object:
            log.warning(f"Location not found for CID retrieval: {location}")
            return None
        
        google_cid = self._get_attribute(zip_code_object, 'google_cid')
        if google_cid:
            log.debug(f"Google CID retrieved for location {location}: {zip_code_object}")
            return zip_code_object
        
        log.warning(f"Location not found for CID retrieval: {location}")
        return None
    
    def verify_cid(self, cid: str) -> bool:
        """
        Verify if the provided Google CID is valid.
        """
        #TODO: We need to have this check google to verify if the cid is valid
        # For now, we will just check if it is in the correct format
        
        return False