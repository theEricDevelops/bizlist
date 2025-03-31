import logging
import os
import csv

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base

from sqlalchemy import Column, String, Float, Integer
from sqlalchemy.dialects.postgresql import UUID

Base = declarative_base()

log = logging.getLogger('script-load-zip-data')

class ZipCode(Base):
    __tablename__ = "zip_codes"
    zip = Column(String, primary_key=True, unique=True, nullable=False)
    plus4 = Column(Integer, nullable=True)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    county = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    timezone = Column(String, nullable=True)

def get_db_engine():
    """Creates the SQLAlchemy engine only when called."""
    DATABASE_URL = os.getenv("DATABASE_URL")
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    return engine

def get_db():
    """Creates the SQLAlchemy session only when called."""
    engine = get_db_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
                    city = row['place name']
                    state = row['admin code1']
                    county = row['admin name2']
                    zip_data[zip_code] = (lat, lon, city, state, county)
                log.info(f"Loaded {len(zip_data)} zip codes from {csv_path}")
                return zip_data
        except FileNotFoundError:
            log.error(f"CSV file not found: {csv_path}")
            return {}
        except KeyError as e:
            log.error(f"Missing column in CSV: {e}")
            return {}
        except ValueError as e:
            log.error(f"Error parsing CSV: {e}")
            return {}
        
def add_zip_data_to_db(db, zip_data):
    """Adds zip code data to the database."""
    existing_zips = db.query(ZipCode.zip).all()
    existing_zips = {zip_code[0] for zip_code in existing_zips}

    for zip_code, (lat, lon, city, state, county) in zip_data.items():

        if zip_code in existing_zips:
            log.debug(f"Zip code {zip_code} already exists in the database. Skipping.")
            continue
        
        zip_entry = ZipCode(
            zip=zip_code,
            latitude=lat,
            longitude=lon,
            city=city,
            state=state,
            county=county
        )
        db.add(zip_entry)
    db.commit()
    log.info(f"Added {len(zip_data)} zip codes to the database.")

if __name__ == "__main__":
    print(f"Starting zip code data loading script...")
    db = next(get_db())
    zip_data = load_zip_code_data()
    if zip_data:
        print(f"Loaded {len(zip_data)} zip codes from CSV.")
        print(f"First entry of zip_data is: {list(zip_data.items())[0]}")
        # Add all zip data into db
        add_zip_data_to_db(db, zip_data)
        print(f"Added {len(zip_data)} zip codes to the database.")
    else:
        print(f"No zip data loaded. Exiting.")
        log.error("No zip data loaded. Exiting.")
    log.info("Zip code data loading script completed.")
    print(f"Zip code data loading script completed.")
    db.close()