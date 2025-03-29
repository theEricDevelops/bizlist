from pydantic import BaseModel, Field
from pydantic.networks import EmailStr, HttpUrl
from typing import Optional, List
import uuid


class BusinessSchemaBase(BaseModel):
    name: str
    industry: Optional[str] = None
    address: Optional[str] = None
    address2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    email: Optional[EmailStr] = None
    notes: Optional[List[str]] = None

    class Config:
        from_attributes = True
        max_recursion = 1

class ContactSchemaBase(BaseModel):
    id: Optional[uuid.UUID] = Field(default=None)
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True
        max_recursion = 1

class BusinessSchemaCreate(BusinessSchemaBase):
    id: Optional[uuid.UUID] = Field(default=uuid.uuid4())

    class Config:
        from_attributes = True
        max_recursion = 1

class BusinessSchemaRef(BusinessSchemaBase):
    pass

class ContactSchemaRef(ContactSchemaBase):
    pass

class BusinessSchema(BusinessSchemaBase):
    contacts: List[ContactSchemaRef] = []
    sources: List["SourceSchemaRef"] = []

    class Config:
        from_attributes = True
        max_recursion = 1

class ContactSchema(ContactSchemaBase):
    businesses: List[BusinessSchemaRef] = []
    sources: List["SourceSchemaRef"] = []

    class Config:
        from_attributes = True
        max_recursion = 1

class BusinessContactSchema(BaseModel):
    id: Optional[uuid.UUID] = Field(default=uuid.uuid4())
    business_id: uuid.UUID
    contact_id: uuid.UUID

    class Config:
        from_attributes = True
        max_recursion = 1

