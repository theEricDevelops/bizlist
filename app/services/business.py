import os
import csv 
import time
from app.main import config
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List
from app.models.contacts import Business
from app.schemas import BusinessSchema
from app.services.logger import Logger
from app.services.formatter import Formatter
from app.services.exporter import Exporter
from app.models.source import BusinessSource, Source
from app.schemas import SourceData

log = Logger('service-business')
format = Formatter()


class BusinessService:
    def __init__(self):
        pass

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

    def add(self, db: Session, company: SourceData):
        source = db.execute(select(Source).where(Source.id == company.source_id)).scalar_one_or_none()
        data = company.data
        name = str(data.get("name")).capitalize()
        industry = str(data.get("industry")).capitalize() or ""
        email = format.email(data.get("email")) or ""
        phone_number = format.phone(data.get("phone")) or ""
        address, address2, city, state, zip = format.address_parts(data.get("address"))
        zip = format.zip(zip) or ""
        website = format.website(data.get("website")) or ""
        business = Business(
            name=name, industry=industry, email=email, phone=phone_number,
            address=address, address2=address2, city=city, state=state, zip=zip,
            website=website, notes=str(data)
        )
        existing_business = db.query(Business).filter(Business.name == name).first()
        if existing_business:
            log.info(f"Found existing business: {name} (ID: {existing_business.id})")
            updated_business = self.update(db, existing_business, business)
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
            log.debug(f"Adding new business: {business}")    
            db.add(business)
            db.flush()
            if source:
                business_source = BusinessSource(business_id=business.id, source_id=source.id)
                db.add(business_source)
            db.commit()
            return {"existing": False, "business": business}
    
    def export_to_csv(data: List[Business], filename: str = None) -> str:
        export = Exporter()
        return export.to_csv(data)