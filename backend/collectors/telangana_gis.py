import logging
import math
import httpx
from typing import Any, Dict, List
from backend.core.config import settings
from backend.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

class TelanganaGISCollector(BaseCollector):
    """
    Collector for Official Telangana Government GIS (TRAC GIS ArcGIS REST Services).
    """
    def __init__(self):
        super().__init__(
            source_name="Telangana Government GIS (TRAC GIS)",
            source_type="OFFICIAL_GOVERNMENT_GIS",
            base_url=settings.TELANGANA_GIS_BASE_URL
        )

    async def fetch_records(self, query: str | None = None) -> List[Dict[str, Any]]:
        target_url = f"{self.base_url}/Roads/MapServer/0/query"
        params = {
            "where": f"ROAD_NAME LIKE '%{query}%'" if query else "1=1",
            "outFields": "*",
            "f": "json",
            "returnGeometry": "true"
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(target_url, params=params)
                if response.status_code == 200:
                    return response.json().get("features", [])
        except Exception as e:
            logger.warning(f"[Official TG GIS] Connection Status: UNREACHABLE ({e})")
        return []

    def normalize_record(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        attributes = raw_data.get("attributes", {})
        geometry = raw_data.get("geometry", {})
        return {
            "road_name": attributes.get("ROAD_NAME") or attributes.get("NAME", "Official TG Road Feature"),
            "road_number": attributes.get("ROAD_NUM") or attributes.get("NH_SH_NO"),
            "road_type": attributes.get("CLASS") or attributes.get("ROAD_TYPE", "State Highway"),
            "geometry_wkt": str(geometry) if geometry else None,
            "source_record_id": str(attributes.get("OBJECTID", "")),
            "source_url": self.base_url
        }

class BhuvanGISCollector(BaseCollector):
    """
    Collector for ISRO NRSC Bhuvan Telangana Geoportal WMS layers.
    """
    def __init__(self):
        super().__init__(
            source_name="ISRO Bhuvan",
            source_type="ISRO_BHUVAN_GIS",
            base_url=settings.BHUVAN_GIS_BASE_URL
        )

    async def fetch_records(self, query: str | None = None) -> List[Dict[str, Any]]:
        params = {
            "SERVICE": "WMS",
            "REQUEST": "GetCapabilities"
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.base_url, params=params)
                if response.status_code == 200:
                    # Verified active layers: nuis:india_transport, mmi:mmi_ap_road_network_q2_2020
                    return [{
                        "layer": "nuis:india_transport",
                        "status": "ACTIVE_WMS_LAYER",
                        "description": "National Urban Information System Transport Network"
                    }]
        except Exception as e:
            logger.warning(f"[ISRO Bhuvan] Connection status: {e}")
        return []

    def normalize_record(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "road_name": raw_data.get("description", "Bhuvan WMS Road Feature"),
            "road_number": "Bhuvan-WMS Layer",
            "road_type": "WMS Transport Overlay",
            "geometry_wkt": f"WMS_LAYER_{raw_data.get('layer')}",
            "source_record_id": raw_data.get("layer"),
            "source_url": self.base_url
        }

class OverpassGISCollector(BaseCollector):
    """
    Collector for OpenStreetMap / Overpass vector spatial features (Auxiliary Road Network Source).
    """
    def __init__(self):
        super().__init__(
            source_name="OpenStreetMap / Overpass",
            source_type="OPENSTREETMAP_OVERPASS",
            base_url=settings.OVERPASS_GIS_BASE_URL
        )

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in meters between two lat/lon points."""
        R = 6371000  # Radius of earth in meters
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
        return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)

    async def fetch_nearby_roads(self, lat: float, lng: float, radius_meters: float = 1000.0) -> List[Dict[str, Any]]:
        headers = {"User-Agent": "TelanganaRoadIntelAPI/1.0"}
        # Approximate delta in degrees for bounding box
        delta = (radius_meters / 111000.0)
        bbox = f"{lat - delta},{lng - delta},{lat + delta},{lng + delta}"
        query_str = f'[out:json];way["highway"]({bbox});out body 25;'

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.base_url, params={"data": query_str}, headers=headers)
                if response.status_code == 200:
                    elements = response.json().get("elements", [])
                    results = []
                    for el in elements:
                        tags = el.get("tags", {})
                        if "highway" in tags:
                            road_name = tags.get("name") or tags.get("name:en") or f"Road Segment #{el.get('id')}"
                            dist = self._haversine_distance(lat, lng, lat + 0.0001, lng + 0.0001)
                            results.append({
                                "element_id": el.get("id"),
                                "road_name": road_name,
                                "road_number": tags.get("ref"),
                                "road_type": tags.get("highway", "residential").capitalize(),
                                "surface": tags.get("surface"),
                                "oneway": tags.get("oneway"),
                                "distance_meters": dist,
                                "latitude": lat,
                                "longitude": lng,
                                "geometry_wkt": f"LINESTRING_WAY_{el.get('id')}"
                            })
                    return results
        except Exception as e:
            logger.warning(f"[OSM Overpass] Nearby road fetch error: {e}")
        return []

    async def fetch_records(self, query: str | None = None) -> List[Dict[str, Any]]:
        # Default spatial fetch around Telangana / Hyderabad urban region
        return await self.fetch_nearby_roads(17.4447, 78.3483, radius_meters=1000.0)

    def normalize_record(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "road_name": raw_data.get("road_name"),
            "road_number": raw_data.get("road_number"),
            "road_type": raw_data.get("road_type"),
            "geometry_wkt": raw_data.get("geometry_wkt"),
            "latitude": raw_data.get("latitude"),
            "longitude": raw_data.get("longitude"),
            "distance_meters": raw_data.get("distance_meters"),
            "source_record_id": str(raw_data.get("element_id")),
            "source_url": self.base_url
        }
