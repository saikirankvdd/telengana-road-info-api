from pydantic import BaseModel, ConfigDict
from backend.schemas.authority import AuthorityResponse

class ContractorBase(BaseModel):
    contractor_name: str
    company_name: str | None = None
    email: str | None = None
    phone: str | None = None
    official_url: str | None = None
    address: str | None = None
    source_url: str | None = None

class ContractorCreate(ContractorBase):
    pass

class ContractorResponse(ContractorBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class ProjectContractorResponse(BaseModel):
    contractor: ContractorResponse
    role: str
    award_date: str | None = None
    contract_value: float | None = None

    model_config = ConfigDict(from_attributes=True)

class FallbackContact(BaseModel):
    type: str = "AUTHORITY"
    name: str
    official_email: str | None = None
    official_phone: str | None = None
    official_url: str | None = None

class ContractorIntelligenceResponse(BaseModel):
    contractor: ContractorResponse | None = None
    role: str | None = None
    fallback_contact: FallbackContact | None = None
