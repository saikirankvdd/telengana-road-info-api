from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.services.tender_service import TenderService
from backend.schemas.tender import TenderResponse

router = APIRouter(prefix="/tenders", tags=["Tenders"])

@router.get("", response_model=list[TenderResponse], summary="List all tenders")
def list_tenders(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    tender_service = TenderService(db)
    return tender_service.list_tenders(skip=skip, limit=limit)

@router.get("/{tender_id}", response_model=TenderResponse, summary="Get tender by ID or tender reference code")
def get_tender(tender_id: str, db: Session = Depends(get_db)):
    tender_service = TenderService(db)
    tender = None
    if tender_id.isdigit():
        tender = tender_service.get_tender_by_id(int(tender_id))
    if not tender:
        tender = tender_service.get_tender_by_code(tender_id)

    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tender '{tender_id}' not found."
        )
    return tender
