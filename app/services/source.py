from app.models.source import Source
from app.schemas import SourceSchema
from sqlalchemy.orm import Session
import uuid
from app.services.logger import Logger

log = Logger('service-source')

def add_or_find_source(db: Session, source: SourceSchema) -> uuid.UUID:
    source_name = source.name
    source_url = source.url
    existing_source = db.query(Source).filter(Source.name == source_name).first()
    if not existing_source:
        new_source = Source(name=source_name, url=source_url)
        db.add(new_source)
        db.commit()
        db.refresh(new_source)
        log.info(f"Added new source: {new_source.name} (ID: {new_source.id})")
        return new_source.id
    else:
        log.info(f"Found existing source: {existing_source.name} (ID: {existing_source.id})")
        return existing_source.id