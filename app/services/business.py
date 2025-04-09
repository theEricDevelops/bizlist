from uuid import UUID
from datetime import datetime
from app.core.config import config
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from typing import List, Optional
from app.models.contact import Business
from app.schemas.contact import BusinessSchema, BusinessSchemaRead, BusinessSchemaCreate
from app.services.logger import Logger
from app.services.formatter import Formatter
from app.services.exporter import Exporter
from app.services.source import SourceService
from app.models.source import Source
from app.models.joins import BusinessSource
from app.schemas.source import SourceData
from app.schemas.core import APIResponse, BusinessResponse

from urllib.parse import unquote_plus

log = Logger('service-business')
format = Formatter()
sources = SourceService()

class BusinessService:
    def __init__(self):
        pass

    def _serialize_business(self, business: Business) -> dict:
        """Serialize a Business object to a dictionary."""
        business_dict = business.__dict__.copy()
        business_dict.pop('_sa_instance_state', None)

        keys_to_process = list(business_dict.keys())

        processed_dict = {}
        for key in keys_to_process:
            value = business_dict[key]
            
            if value == '' or value is None:
                continue

            if isinstance(value, UUID):
                processed_dict[key] = str(value)
            elif isinstance(value, datetime):
                processed_dict[key] = value.isoformat(' ', 'seconds')
            else:
                processed_dict[key] = value

        return processed_dict

    def update(self, db: Session, business: Business, data: BusinessSchema) -> Business:
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
        log.info(f"Updated business: {business.name} (ID: {business.id})")
        return business

    def add(self, db: Session, data: BusinessSchemaCreate) -> BusinessSchema:
        """Add a new business to the database."""
        log.info(f"Adding new business: {data}")
        errors = []
        status = 'success'
        code = 201
        params = data
        result_data = {}

        try:
            name = format.name(str(params['name']))
            existing_business: Business = db.query(Business).filter(Business.name == name).first()
            log.debug(f"Existing business: {existing_business}")

            if existing_business:
                log.warning(f"Business with name '{name}' already exists.")
                errors.append(f"Business with name '{name}' already exists.")
                return 'error', 409, errors, {"name": name}, self._serialize_business(existing_business)

            #source = db.execute(select(Source).where(Source.id == data.source_id)).scalar_one_or_none()
            _, _, _, _, source = sources.get(db, search=data['source'])
            log.debug(f"Source: {source}")
            
            if not source or 'sources' not in source or not source['sources']:
                log.error(f"Invalid source structure: {source}")
                errors.append("Invalid source structure.")
                return 'error', 500, errors, params, result_data
            
            source_id = source['sources'][0]['id']
            log.debug(f"Source ID: {source_id} (type: {type(source_id)})")
            
            log.debug(f"Name: {name}")
            if data.get("industry"):
                industry = format.name(str(data.get("industry"))) or ""
                log.debug(f"Industry: {industry}")
            else: 
                industry = ""
            if data.get("email"):
                email = format.email(data.get("email")) or ""
                log.debug(f"Email: {email}")
            else:
                email = ""
            if data.get("phone"):
                phone_number = format.phone(data.get("phone")) or ""
                log.debug(f"Phone: {phone_number}")
            else:
                phone_number = ""
            if data.get("address"):
                address, address2, city, state, zip = format.address_parts(data.get("address"))
                zip = format.zip(zip) or ""
                log.debug(f"Address: {address}, Address2: {address2}, City: {city}, State: {state}, Zip: {zip}")
            else:
                address = address2 = city = state = zip = ""
            if data.get("website"):
                website = format.website(data.get("website")) or ""
                log.debug(f"Website: {website}")
            else:
                website = ""
            
            business = Business(
                name=name, industry=industry, email=email, phone=phone_number,
                address=address, address2=address2, city=city, state=state, zip=zip,
                website=website, notes=str(data)
            )
            log.debug(f"Business object: {business}")
            db.add(business)
            db.flush()
            db.refresh(business)
            log.info(f"Added new business: {business.name} (ID: {business.id})")
            
            # Create a new BusinessSource object and associate it with the business
            business_source = BusinessSource(business_id=business.id, source_id=source_id)
            db.add(business_source)
            db.commit()
            db.refresh(business)
            log.info(f"Added source to business: {business.name} (ID: {business.id})")

            business_dict = {
                "id": str(business.id) if business.id else None,
                "name": business.name,
                "phone": business.phone,
                "email": business.email,
                "address": business.address,
                "address2": business.address2,
                "city": business.city,
                "state": business.state,
                "zip": business.zip,
                "website": business.website,
                "industry": business.industry,
                "source": source['sources'][0]['name'] if source['sources'] else None,
                "notes": business.notes,
            }

            return 'success', 201, errors, data, business_dict
        except SQLAlchemyError as e:
            log.error(f"Error adding business: {e}")
            errors.append(f"Error adding business: {e}")
            return 'error', 500, [str(e)], params, result_data
        except Exception as e:
            log.error(f"Unexpected error: {e}")
            errors.append(f"Unexpected error: {e}")
            return 'error', 500, [str(e)], params, result_data
        
    def get(self, db: Session, params: dict = None) -> Optional[List[Business]]:
        errors = []
        original_params = params.copy() if params else {}
        
        if 'limit' in params:
            limit = params.pop('limit')
            if not isinstance(limit, int):
                try:
                    limit = int(limit)
                except ValueError:
                    log.warning(f"Invalid limit value: {limit}. Setting to default (10).")
                    limit = 10
                    errors.append("Limit must be an integer. Used default (10).")
            elif limit < 1 or limit > 100:
                log.warning(f"Invalid limit value: {limit}. Setting to default (10).")
                limit = 10
                errors.append("Limit must be between 1 and 100. Used default (10).")
        else:
            limit = 10

        if 'skip' in params:
            skip = params.pop('skip')
            if not isinstance(skip, int):
                try:
                    skip = int(skip)
                except ValueError:
                    log.warning(f"Invalid skip value: {skip}. Setting to default (0).")
                    skip = 0
                    errors.append("Skip must be an integer. Used default (0).")
            elif skip < 0:
                log.warning(f"Invalid skip value: {skip}. Setting to default (0).")
                skip = 0
                errors.append("Skip must be a non-negative integer. Used default (0).")
        else:
            skip = 0

        try:
            # Build dynamic query
            query = db.query(Business)
            if params:    
                # Apply filters from query parameters
                invalid_params = []
                for key, value in params.items():
                    if hasattr(Business, key):
                        # Make sure the value is properly decoded and sanitized
                        value = unquote_plus(value)

                        query = query.filter(getattr(Business, key).ilike(f"%{value}%"))
                    else:
                        invalid_params.append(key)
                
                if invalid_params:
                    log.warning(f"Invalid query parameters: {invalid_params}")
                    errors.append(f"Invalid query parameters: {invalid_params}")
                    # Return error response if there are invalid parameters
                    return 400, 'error', errors, original_params, None
                
                query = query.offset(skip).limit(limit)
                businesses = query.all()
                log.info(f"Found {len(businesses)} businesses matching criteria")
                
            else:
                log.debug("No query parameters provided, returning all businesses")
                businesses = query.offset(skip).limit(limit).all()

            if not businesses:
                log.warning("No businesses found matching criteria {original_params}")
                errors.append("No businesses found matching criteria.")
                return 404, 'error', errors, original_params, None

            log.debug(f"Business objects: {businesses}")
            log.info(f"Returning {len(businesses)} businesses")

            business_list = []
            for business in businesses:
                business_dict = business.__dict__.copy()
                business_dict.pop('_sa_instance_state', None)

                keys_to_process = list(business_dict.keys())

                processed_dict = {}
                for key in keys_to_process:
                    value = business_dict[key]
                    
                    if value == '' or value is None:
                        continue

                    if isinstance(value, UUID):
                        processed_dict[key] = str(value)
                    else:
                        processed_dict[key] = value

                try:
                    business_model = BusinessSchemaRead.model_validate(processed_dict)

                    business_data = business_model.model_dump()

                    for key, value in business_data.items():
                        if isinstance(value, UUID):
                            business_data[key] = str(value)

                    business_list.append(business_data)
                except Exception as e:
                    log.error(f"Error validating business model: {e}")
                    
                    for key, value in processed_dict.items():
                        if isinstance(value, UUID):
                            processed_dict[key] = str(value)
                    business_list.append(processed_dict)

            params.update({"limit": limit, "skip": skip})
            data = business_list
            return 200, 'success', errors, params, data
        except SQLAlchemyError as e:
            log.error(f"Error reading businesses: {e}")
            return 500, 'error', [f"Database error: {e}"], original_params, None
        except ValueError as e:
            log.error(f"Value error: {e}")
            return 400, 'error', [f"Value error: {e}"], original_params, None
        except Exception as e:
            log.error(f"Unexpected error: {e}")
            return 500, 'error', [f"Unexpected error: {e}"], original_params, None
    
    def remove(self, db: Session, business: Business) -> tuple[str, int, list, dict, dict]:
        """Remove a business from the database."""
        log.info(f"Removing business: {business.name} (ID: {business.id})")
        errors = []
        code = 200
        params = {
            "business": business.model_dump()
        }
        data = {
            "business": None
        }

        try:
            db.delete(business)
            db.commit()
            log.info(f"Removed business: {business.name} (ID: {business.id})")
            return 'success', code, errors, params, data
        except SQLAlchemyError as e:
            log.error(f"Error removing business: {e}")
            errors.append(f"Error removing business: {e}")
            return 'error', 500, [str(e)], params, data
        except Exception as e:
            log.error(f"Unexpected error: {e}")
            errors.append(f"Unexpected error: {e}")
            return 'error', 500, [str(e)], params, data
    
    def export_to_csv(data: List[Business], filename: str = None) -> str:
        export = Exporter()
        return export.to_csv(data)