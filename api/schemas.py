from pydantic import BaseModel, Field
from typing import Optional, List, Union
import uuid

class BusinessSchema(BaseModel):
    id: Optional[uuid.UUID] = Field(default=None)
    name: str
    industry: Optional[str] = None
    address: Optional[str] = None
    address2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None
    sources: List["SourceSchema"] = []

    class Config:
        from_attributes = True

class ContactSchema(BaseModel):
    id: Optional[uuid.UUID] = Field(default=None)
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    notes: Optional[str] = None
    businesses: List["BusinessSchema"] = []
    sources: List["SourceSchema"] = []

    class Config:
        from_attributes = True

class BusinessContactSchema(BaseModel):
    business_id: uuid.UUID
    contact_id: uuid.UUID

    class Config:
        from_attributes = True

class SourceSchema(BaseModel):
    id: Optional[uuid.UUID] = Field(default=None)
    name: str
    url: Optional[str] = None
    notes: Optional[str] = None
    businesses: List["BusinessSchema"] = []
    contacts: List["ContactSchema"] = []

    class Config:
        from_attributes = True

class SourceData(BaseModel):
    source_id: uuid.UUID
    data: dict

    class Config:
        from_attributes = True

class LocationSchema(BaseModel):
    zipCode: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None

    class Config:
        from_attributes = True

class CoverageZipListSchema(BaseModel):
    id: Optional[uuid.UUID] = Field(default=None, description="Unique identifier for the coverage zip list")
    params: str = Field(..., description="Parameters used to generate the zip list (e.g., state, radius)")
    zips: str = Field(..., description="Comma-separated list of zip codes")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "params": "state=Tennessee,radius=25",
                "zips": "37010,37011,37012,37013"
            }
        }