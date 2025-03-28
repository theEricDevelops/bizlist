from sqlalchemy import Column, String, Float, Boolean
from app.models import Base, generate_uuid
from sqlalchemy.dialects.postgresql import UUID

class ZipCode(Base):
    __tablename__ = "zip_codes"
    zip = Column(String, primary_key=True, unique=True, nullable=False)
    plus4 = Column(Boolean, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    county = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    timezone = Column(String, nullable=True)

class CoverageZipList(Base):
    __tablename__ = "coverage_zip_list"
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    params = Column(String, unique=True, nullable=False)
    zips = Column(String, nullable=False)