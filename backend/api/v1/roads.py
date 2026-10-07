from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.services.gis_service import GISService
from backend.schemas.road import RoadResponse

router = APIRouter(prefix="/roads", tags=["Roads"])

@router.get("", response_model=list[RoadResponse], summary="List all registered roads")
async def list_roads(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    gis_service = GISService(db)
    return await gis_service.list_roads(skip=skip, limit=limit)

@router.get("/{road_id}", response_model=RoadResponse, summary="Get road by ID")
async def get_road(road_id: int, db: Session = Depends(get_db)):
    gis_service = GISService(db)
    road = await gis_service.get_road_by_id(road_id)
    if not road:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Road with ID {road_id} not found."
        )
    return road
