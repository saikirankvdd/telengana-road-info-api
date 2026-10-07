from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.models.authority import Authority
from backend.schemas.authority import AuthorityResponse

router = APIRouter(prefix="/authorities", tags=["Authorities"])

@router.get("", response_model=list[AuthorityResponse], summary="List all government authorities")
def list_authorities(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(Authority).offset(skip).limit(limit).all()

@router.get("/{authority_id}", response_model=AuthorityResponse, summary="Get authority by ID")
def get_authority(authority_id: int, db: Session = Depends(get_db)):
    authority = db.query(Authority).filter(Authority.id == authority_id).first()
    if not authority:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Authority with ID {authority_id} not found."
        )
    return authority
