from pydantic import BaseModel, Field
from typing import Optional, List
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
    id: Optional[uuid.UUID] = Field(default=uuid.uuid4())
    business_id: uuid.UUID
    contact_id: uuid.UUID

    class Config:
        from_attributes = True
