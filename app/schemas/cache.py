from pydantic import BaseModel, Field
from typing import Optional
import uuid

class WebSearchCacheSchema(BaseModel):
    id: Optional[uuid.UUID] = Field(default=None, description="Unique identifier for the web search cache")
    params: dict = Field(..., description="Parameters used to generate the search results")
    data: dict = Field(..., description="Results from web search")

    class Config:
        from_attributes = True