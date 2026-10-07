from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.services.intelligence_service import IntelligenceService
from backend.services.gis_service import GISService

router = APIRouter(tags=["Road Intelligence & Spatial GIS"])

@router.get("/road-intelligence", summary="Unified Road & Project Intelligence")
async def get_road_intelligence(
    query: str | None = Query(None, description="Project or road search query (e.g. 'IIIT Junction')"),
    lat: float | None = Query(None, description="Latitude coordinate"),
    lng: float | None = Query(None, description="Longitude coordinate"),
    project_id: str | None = Query(None, description="Specific project code"),
    db: Session = Depends(get_db)
):
    intel_service = IntelligenceService(db)
    return await intel_service.get_road_intelligence(
        query=query,
        lat=lat,
        lng=lng,
        project_id=project_id
    )

@router.get("/nearby", summary="Find nearby roads & spatial vector features by coordinates")
async def get_nearby_roads(
    lat: float = Query(..., description="Latitude coordinate (e.g. 17.4447)"),
    lng: float = Query(..., description="Longitude coordinate (e.g. 78.3483)"),
    radius: float = Query(1000.0, description="Radius search distance in meters"),
    db: Session = Depends(get_db)
):
    """
    Coordinate-based geographic search:
    lat + lng -> spatial query -> nearest roads -> geometry + distance + administrative info + provenance
    """
    gis_service = GISService(db)
    return await gis_service.get_nearby_roads(lat=lat, lng=lng, radius_meters=radius)
