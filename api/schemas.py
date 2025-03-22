from pydantic import BaseModel, Field

class BusinessSchema(BaseModel):
    id: int | None = Field(default=None)
    name: str
    industry: str | None = None
    location: str | None = None

    class Config:
        orm_mode = True

class ContactSchema(BaseModel):
    id: int | None = Field(default=None)
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    title: str | None = None

    class Config:
        orm_mode = True

class BusinessContactSchema(BaseModel):
    business_id: int
    contact_id: int

    class Config:
        orm_mode = True

