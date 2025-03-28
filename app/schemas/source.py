from pydantic import BaseModel, Field
from typing import Optional, List
import uuid

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