from app.models.source import Source
from app.schemas.source import SourceSchemaBase, SourceSchema
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import uuid
from urllib.parse import unquote_plus
from app.services.logger import Logger

log = Logger('service-source')

class SourceService:
    def __init__(self):
        pass

    def get(self, db: Session, skip: int = 0, limit: int = 100, search: str = None) -> tuple[str, int, list, dict, dict]:
        """Get sources from the database with optional pagination and search."""
        log.info(f"Getting sources with pagination: skip={skip}, limit={limit}, search={search}")
        errors = []
        status = 'success'
        code = 200
        params = {
            "skip": skip,
            "limit": limit,
            "search": search
        }
        data = {
            "total": 0,
            "sources": []
        }

        try:
            skip = int(skip) if skip is not None else 0
            limit = int(limit) if limit is not None else 100
        except ValueError as e:
            log.error(f"Invalid pagination parameters: {e}. Using defaults (0, 100).")
            errors.append(f"Invalid pagination parameters: {e}. Using defaults (0, 100).")
            skip = 0
            limit = 100
        
        try:
            query = db.query(Source)
            log.debug(f"Initial query: {query}")

            if search and isinstance(search, str):
                log.debug(f"Search term: {search}")
                search = search.strip()
                search = unquote_plus(search)
                if search:
                    query = query.filter(Source.name.ilike(f"%{search}%"))

            total_count = query.count()
            log.debug(f"Total count of sources: {total_count}")
            data["total"] = total_count
                        
            #source_list = query.offset(skip).limit(limit).all()
            source_list = query.all()
            log.debug(f"Source list: {source_list}")

            if not source_list:
                log.warning("No sources found.")
                errors.append("No sources found.")
                code = 404
                status = 'error'

            sources = []
            for source in source_list:
                log.debug(f"Processing source: {source}")
                source_obj = SourceSchemaBase.model_validate(source)
                source_dict = source_obj.model_dump()
                source_dict["id"] = str(source_dict["id"]) if source_dict["id"] else None
                sources.append(source_dict)
                log.debug(f"Source dict: {source_dict}")
            data["sources"] = sources
            log.debug(f"Final data: {data}")

            return (
                status, 
                code, 
                errors, 
                params, 
                data
            )
        except SQLAlchemyError as e:
            log.error(f"Error getting sources: {e}")
            return (
                "error", 
                500, 
                [str(e)], 
                params,
                data
            )
        except Exception as e:
            log.error(f"Unexpected error: {e}")
            return (
                "error", 
                500, 
                [str(e)], 
                params, 
                data
            )

    def add(self, db: Session, source: SourceSchema) -> tuple[str, int, list, dict, dict]:
        """Add a new source to the database."""
        log.info(f"Adding new source: {source}")
        errors = []
        code = 200
        params = {
            "source": source.model_dump()
        }
        data = {
            "sources": []
        }

        try:
            source_exists = db.query(Source).filter(Source.name == source.name).first()
            if source_exists:
                source_obj = SourceSchemaBase.model_validate(source_exists)
                source_dict = source_obj.model_dump()
                source_dict["id"] = str(source_dict["id"]) if source_dict["id"] else None

                data["sources"] = [source_dict]
                log.debug(f"Source already exists: {source_exists}")
                log.warning(f"Source already exists: {source.name}")
                errors.append("Source already exists.")
                code = 409
                return (
                    'error', 
                    code, 
                    errors, 
                    params, 
                    data
                )
            else:
                try:
                    new_source = Source(
                        name=source.name,
                        url=source.url,
                        notes=source.notes
                    )
                    db.add(new_source)
                    db.commit()
                    db.refresh(new_source)
                    log.info(f"Added new source: {new_source.name} (ID: {new_source.id})")
                    source_obj = SourceSchemaBase.model_validate(new_source)
                    source_dict = source_obj.model_dump()
                    source_dict["id"] = str(source_dict["id"]) if source_dict["id"] else None

                    data["sources"] = [source_dict]
                    log.debug(f"New source dict: {source_dict}")
                    code = 201
                except SQLAlchemyError as e:
                    log.error(f"Error adding source: {e}")
                    errors.append(f"Error adding source: {e}")
                    code = 500
                    return (
                        "error", 
                        code, 
                        errors, 
                        params,
                        data
                    )
                except Exception as e:
                    log.error(f"Unexpected error: {e}")
                    errors.append(f"Unexpected error: {e}")
                    code = 500
                    return (
                        "error", 
                        code, 
                        errors, 
                        params,
                        data
                    )
            if not errors:
                log.info(f"Source added successfully: {source.name} (ID: {new_source.id})")
                return (
                    'success', 
                    code, 
                    errors, 
                    params, 
                    data
                )
            else:
                log.warning(f"Errors occurred while adding source: {errors}")
                return (
                    'error', 
                    code, 
                    errors, 
                    params, 
                    data
                )
        except ValueError as e:
            log.error(f"Invalid source data: {e}")
            errors.append(f"Invalid source data: {e}")
            return (
                "error", 
                400, 
                errors, 
                params,
                data
            )
        except TypeError as e:
            log.error(f"Type error: {e}")
            errors.append(f"Type error: {e}")
            return (
                "error", 
                400, 
                errors, 
                params,
                data
            )
        except AttributeError as e:
            log.error(f"Attribute error: {e}")
            errors.append(f"Attribute error: {e}")
            return (
                "error", 
                400, 
                errors, 
                params,
                data
            )
        except KeyError as e:
            log.error(f"Key error: {e}")
            errors.append(f"Key error: {e}")
            return (
                "error", 
                400, 
                errors, 
                params,
                data
            )
        except IndexError as e:
            log.error(f"Index error: {e}")
            errors.append(f"Index error: {e}")
            return (
                "error", 
                400, 
                errors, 
                params,
                data
            )
        except SQLAlchemyError as e:
            log.error(f"Error adding source: {e}")
            return (
                "error", 
                500, 
                [str(e)], 
                params,
                data
            )
        except Exception as e:
            log.error(f"Unexpected error: {e}")
            return (
                "error", 
                500, 
                [str(e)], 
                params, 
                data
            )

#TODO: Refactor to eliminate this function and use the add method instead
def add_or_find_source(source: SourceSchema, db: Session) -> uuid.UUID:
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