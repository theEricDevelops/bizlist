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

class ZipCodeSchema(BaseModel):
    zip: str = Field(default=None, description="The zip code")
    plus4: bool = Field(default=False, description="Whether the zip code has a plus 4 extension")
    city: str = Field(default=None, description="The city associated with the zip code")
    state: str = Field(default=None, description="The state associated with the zip code")
    county: Optional[str] = Field(default=None, description="The county associated with the zip code")
    latitude: Optional[float] = Field(default=None, description="The latitude of the zip code")
    longitude: Optional[float] = Field(default=None, description="The longitude of the zip code")
    timezone: Optional[str] = Field(default=None, description="The timezone of the zip code")

class WebSearchCacheSchema(BaseModel):
    id: Optional[uuid.UUID] = Field(default=None, description="Unique identifier for the web search cache")
    params: dict = Field(..., description="Parameters used to generate the search results")
    data: dict = Field(..., description="Results from web search")

    class Config:
        from_attributes = True

class OwnerSearchSchema(BaseModel):
    company_name: str = Field(description="The name of the company")
    company_phone: str = Field(description="The phone number of the company in digital-only format i.e. 1234567890")
    company_email: str = Field(description="The email address of the company")
    company_address: str = Field(description="The address of the company in proper format i.e. Street, Street 2, City, State, Zip")
    company_website: str = Field(description="The website of the company with protocol i.e. https://example.com")
    company_industry: str = Field(description="The industry of the company")
    owner_name: str = Field(description="The name of the owner")
    owner_phone: str = Field(description="The phone number of the owner in digital-only format i.e. 1234567890")
    owner_email: str = Field(description="The email address of the owner")
    owner_address: str = Field(description="The address of the owner")
    owner_linkedin: str = Field(description="The LinkedIn profile URL of the owner")