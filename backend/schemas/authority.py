from pydantic import BaseModel, ConfigDict

class AuthorityBase(BaseModel):
    name: str
    authority_type: str | None = None
    state: str | None = "Telangana"
    district: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    official_url: str | None = None
    source_url: str | None = None

class AuthorityCreate(AuthorityBase):
    pass

class AuthorityResponse(AuthorityBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class ProjectAuthorityResponse(BaseModel):
    authority: AuthorityResponse
    role: str

    model_config = ConfigDict(from_attributes=True)
