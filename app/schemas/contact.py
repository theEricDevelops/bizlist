from pydantic import BaseModel, Field, field_validator, model_serializer
from pydantic.networks import EmailStr, HttpUrl
from typing import Optional, List
import uuid

from pydantic import ConfigDict


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
    email: Optional[str] = Field(None, description="Business email address.")
    notes: Optional[List[str]] = None

    model_config = ConfigDict(
        from_attributes=True,
        max_recursion=1,
    )

    @field_validator("notes", mode="before")
    def notes_from_string(cls, value):
        if isinstance(value, str):
            return [value]
        return value
    
    @field_validator("notes")
    def join_notes(cls, value: List[str] | None) -> Optional[str]:
        if value is None:
            return None
        return "\n".join(value)
    
    @field_validator("email")
    def validate_email(cls, value: Optional[str]) -> Optional[EmailStr]:
        if value is None:
            return None
        return value
    
    @field_validator("website")
    def validate_website(cls, value: Optional[str]) -> Optional[HttpUrl]:
        if value is None:
            return None
        return value

class ContactSchemaBase(BaseModel):
    id: Optional[uuid.UUID] = Field(default=None)
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        max_recursion=1,
    )

class BusinessSchemaCreate(BusinessSchemaBase):
    id: Optional[uuid.UUID] = Field(default=uuid.uuid4())

    model_config = ConfigDict(
        from_attributes=True,
        max_recursion=1,
    )

class BusinessSchemaRef(BusinessSchemaBase):
    pass

class ContactSchemaRef(ContactSchemaBase):
    pass

class BusinessSchemaRead(BusinessSchemaBase):
    id: uuid.UUID = Field(default=uuid.uuid4())
    
    @model_serializer
    def serialize_model(self):
        # Return a dictionary with fields in the order you want
        return {
            'id': str(self.id),
            'name': self.name,
            'address': self.address,
            'address2': self.address2,
            'city': self.city,
            'state': self.state,
            'zip': self.zip,
            'phone': self.phone,
            'website': self.website,
            'email': self.email,
            'industry': self.industry,
            'notes': self.notes
        }

class BusinessSchema(BusinessSchemaBase):
    contacts: List[ContactSchemaRef] = []
    sources: List["SourceSchemaRef"] = []

    model_config = ConfigDict(
        from_attributes=True,
        max_recursion=1,
    )

class ContactSchema(ContactSchemaBase):
    businesses: List[BusinessSchemaRef] = []
    sources: List["SourceSchemaRef"] = []

    model_config = ConfigDict(
        from_attributes=True,
        max_recursion=1,
    )

class BusinessContactSchema(BaseModel):
    id: Optional[uuid.UUID] = Field(default=uuid.uuid4())
    business_id: uuid.UUID
    contact_id: uuid.UUID

    model_config = ConfigDict(
        from_attributes=True,
        max_recursion=1,
    )

