from sqlalchemy.orm import Session, joinedload
from backend.models.tender import Tender

class TenderService:
    def __init__(self, db: Session):
        self.db = db

    def get_tender_by_id(self, tender_db_id: int) -> Tender | None:
        return (
            self.db.query(Tender)
            .options(joinedload(Tender.source))
            .filter(Tender.id == tender_db_id)
            .first()
        )

    def get_tender_by_code(self, tender_code: str) -> Tender | None:
        return (
            self.db.query(Tender)
            .options(joinedload(Tender.source))
            .filter(Tender.tender_id == tender_code)
            .first()
        )

    def list_tenders(self, skip: int = 0, limit: int = 50) -> list[Tender]:
        return (
            self.db.query(Tender)
            .options(joinedload(Tender.source))
            .offset(skip)
            .limit(limit)
            .all()
        )
