from pydantic import BaseModel, Field

class OwnerSearchSchema(BaseModel):
    company_name: str = Field(description="The name of the company")
    company_phone: str = Field(description="The phone number of the company in digital-only format i.e. 1234567890")
    company_email: str = Field(description="The email address of the company")
    company_address: str = Field(description="The address of the company in proper format i.e. Street, Street 2, City, State, Zip")
    company_website: str = Field(description="The website of the company with protocol i.e. https://example.com")
    company_industry: str = Field(description="The industry of the company")
    owner_name: str = Field(description="The name of the owner")
    owner_phone: str = Field(description="The phone number of the owner in digital-only format i.e. 1234567890")
    owner_email: str = Field(description="The email address of the owner")
    owner_address: str = Field(description="The address of the owner")
    owner_linkedin: str = Field(description="The LinkedIn profile URL of the owner")