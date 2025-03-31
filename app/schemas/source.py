from pydantic import BaseModel, Field
from typing import Optional, List
import uuid


class SourceSchemaBase(BaseModel):
    id: Optional[uuid.UUID] = Field(default=None)
    name: str
    url: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True
        max_recursion = 1

class SourceSchemaRef(SourceSchemaBase):
    pass

class SourceSchema(SourceSchemaBase):
    businesses: List["BusinessSchemaRef"] = []
    contacts: List["ContactSchemaRef"] = []

    class Config:
        from_attributes = True
        max_recursion = 1

class SourceData(BaseModel):
    source_id: uuid.UUID
    data: dict

    class Config:
        from_attributes = True
        max_recursion = 1
