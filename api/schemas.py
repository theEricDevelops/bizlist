from pydantic import BaseModel, Field
from typing import Optional

class BusinessSchema(BaseModel):
    id: int | None = Field(default=None)
    name: str
    industry: str | None = None
    location: str | None = None

    class Config:
        from_attributes = True

class ContactSchema(BaseModel):
    id: int | None = Field(default=None)
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    title: str | None = None

    class Config:
        from_attributes = True

class BusinessContactSchema(BaseModel):
    business_id: int
    contact_id: int

    class Config:
        from_attributes = True

class SourceSchema(BaseModel):
    id: int | None = Field(default=None)
    name: str
    url: Optional[str] = None

    class Config:
        from_attributes = True

class SourceData(BaseModel):
    source_id: int
    data: dict