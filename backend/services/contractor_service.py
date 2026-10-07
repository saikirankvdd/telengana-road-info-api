from sqlalchemy.orm import Session
from backend.models.contractor import Contractor
from backend.models.authority import Authority

class ContractorService:
    def __init__(self, db: Session):
        self.db = db

    def get_contractor_by_id(self, contractor_id: int) -> Contractor | None:
        return self.db.query(Contractor).filter(Contractor.id == contractor_id).first()

    def list_contractors(self, skip: int = 0, limit: int = 50) -> list[Contractor]:
        return self.db.query(Contractor).offset(skip).limit(limit).all()

    def get_authority_fallback(self, primary_authority_id: int | None = None) -> dict:
        """
        Implements Contractor Fallback Principle (Section 11):
        If contractor is not found, return responsible authority details as fallback.
        """
        authority = None
        if primary_authority_id:
            authority = self.db.query(Authority).filter(Authority.id == primary_authority_id).first()
        if not authority:
            authority = self.db.query(Authority).first()

        if authority:
            return {
                "type": "AUTHORITY",
                "name": authority.name,
                "official_email": authority.contact_email,
                "official_phone": authority.contact_phone,
                "official_url": authority.official_url or authority.source_url
            }
        
        return {
            "type": "AUTHORITY",
            "name": "Telangana Roads & Buildings Department (R&B)",
            "official_email": "se-rn-hyderabad@telangana.gov.in",
            "official_phone": "040-23390111",
            "official_url": "https://transport.telangana.gov.in"
        }
