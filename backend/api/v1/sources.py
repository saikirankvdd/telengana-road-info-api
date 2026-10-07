from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.models.source import Source
from backend.schemas.source import SourceResponse

router = APIRouter(prefix="/sources", tags=["Sources & Provenance"])

@router.get("", response_model=list[SourceResponse], summary="List data sources")
def list_sources(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(Source).offset(skip).limit(limit).all()

@router.get("/{source_id}", response_model=SourceResponse, summary="Get source provenance record by ID")
def get_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with ID {source_id} not found."
        )
    return source
