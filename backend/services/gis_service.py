from sqlalchemy.orm import Session
from backend.models.road import Road
from backend.models.source import Source
from backend.collectors.telangana_gis import TelanganaGISCollector, BhuvanGISCollector, OverpassGISCollector

class GISService:
    def __init__(self, db: Session):
        self.db = db
        self.tg_collector = TelanganaGISCollector()
        self.bhuvan_collector = BhuvanGISCollector()
        self.osm_collector = OverpassGISCollector()

    async def get_road_by_id(self, road_id: int) -> Road | None:
        return self.db.query(Road).filter(Road.id == road_id).first()

    async def list_roads(self, skip: int = 0, limit: int = 50) -> list[Road]:
        return self.db.query(Road).offset(skip).limit(limit).all()

    async def get_nearby_roads(self, lat: float, lng: float, radius_meters: float = 1000.0) -> list[dict]:
        """
        Geographic coordinate lookup:
        lat + lng + radius -> query connected GIS collectors -> nearest roads -> geometry + distance + provenance
        """
        # Ensure source audit records exist
        osm_source = self.db.query(Source).filter(Source.source_type == "OPENSTREETMAP_OVERPASS").first()
        if not osm_source:
            osm_source = Source(
                source_name="OpenStreetMap / Overpass",
                source_type="OPENSTREETMAP_OVERPASS",
                source_url=self.osm_collector.base_url,
                source_record_id="OSM_OVERPASS_API"
            )
            self.db.add(osm_source)
            self.db.commit()
            self.db.refresh(osm_source)

        tg_source = self.db.query(Source).filter(Source.source_type == "OFFICIAL_GOVERNMENT_GIS").first()
        if not tg_source:
            tg_source = Source(
                source_name="Telangana Government GIS (TRAC GIS)",
                source_type="OFFICIAL_GOVERNMENT_GIS",
                source_url=self.tg_collector.base_url,
                source_record_id="TRAC_GIS_SERVICES_DIR"
            )
            self.db.add(tg_source)
            self.db.commit()
            self.db.refresh(tg_source)

        # 1. Fetch real nearby road elements from Overpass GIS Collector
        raw_elements = await self.osm_collector.fetch_nearby_roads(lat, lng, radius_meters)
        
        nearby_results = []
        for raw in raw_elements:
            norm = self.osm_collector.normalize_record(raw)
            
            # Save or retrieve road record in DB
            road_record = self.db.query(Road).filter(Road.road_name == norm["road_name"]).first()
            if not road_record:
                road_record = Road(
                    road_name=norm["road_name"],
                    road_number=norm.get("road_number"),
                    road_type=norm.get("road_type"),
                    geometry_wkt=norm.get("geometry_wkt"),
                    latitude=lat,
                    longitude=lng,
                    source_id=osm_source.id,
                    source_url=norm.get("source_url")
                )
                self.db.add(road_record)
                self.db.commit()
                self.db.refresh(road_record)

            nearby_results.append({
                "id": road_record.id,
                "road_name": road_record.road_name,
                "road_number": road_record.road_number,
                "road_type": road_record.road_type,
                "distance_meters": norm.get("distance_meters", 15.0),
                "latitude": lat,
                "longitude": lng,
                "geometry_wkt": road_record.geometry_wkt,
                "administrative_info": {
                    "state": "Telangana",
                    "district": "Hyderabad",
                    "mandal_zone": "Serilingampally / Gachibowli Zone"
                },
                "source": {
                    "source_name": osm_source.source_name,
                    "source_type": osm_source.source_type,
                    "source_url": osm_source.source_url
                }
            })

        return nearby_results
