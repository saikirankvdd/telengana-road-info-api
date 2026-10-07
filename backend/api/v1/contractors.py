from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.services.contractor_service import ContractorService
from backend.schemas.contractor import ContractorResponse

router = APIRouter(prefix="/contractors", tags=["Contractors"])

@router.get("/{contractor_id}", response_model=ContractorResponse, summary="Get contractor by ID")
def get_contractor(contractor_id: int, db: Session = Depends(get_db)):
    service = ContractorService(db)
    contractor = service.get_contractor_by_id(contractor_id)
    if not contractor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contractor with ID {contractor_id} not found."
        )
    return contractor
