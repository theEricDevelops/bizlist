from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Literal, Any

class APIResponse(BaseModel):
    status: Literal["pending", "success", "error"] = Field(None, description="Status of the API response")
    code: int = Field(None, description="HTTP status code")
    errors: Optional[List] = Field([], description="List of errors, if any")
    params: Optional[Dict] = Field({}, description="Parameters used in the API request")
    
class BusinessResponse(APIResponse):
    data: Optional[Dict[str, Any]] = Field({}, description="Data returned by the API, if any")