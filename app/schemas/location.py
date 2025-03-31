from pydantic import BaseModel, Field
from typing import Optional
import uuid

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
    zip: str = Field(default=None, description="The 5-digit zip code")
    plus4: Optional[int] = Field(default=None, description="A plus 4 extension for the zip code")
    city: str = Field(default=None, description="The city associated with the zip code")
    state: str = Field(default=None, description="The state associated with the zip code")
    county: Optional[str] = Field(default=None, description="The county associated with the zip code")
    latitude: Optional[float] = Field(default=None, description="The latitude of the zip code")
    longitude: Optional[float] = Field(default=None, description="The longitude of the zip code")
    timezone: Optional[str] = Field(default=None, description="The timezone of the zip code")
    google_cid: Optional[str] = Field(default=None, description="Google CID for the zip code")

    class Config:
        from_attributes = True