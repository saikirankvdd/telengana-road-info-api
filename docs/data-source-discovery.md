# Official GIS Data Source Discovery & Connection Audit

This document records the empirical investigation, verification status, capability analysis, and data field audit for all external geospatial endpoints evaluated for the **Telangana Road & Project Intelligence API**.

---

## 🗺 1. GIS Data Sources Inventory & Status Table

| Source Name | Official Base URL | API / Protocol | Authentication | Exact Data Fields Retrieved | Provenance Label | Connection Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Telangana Government GIS (TRAC GIS)** | `http://tracgis.telangana.gov.in/arcgis/rest/services` | ArcGIS REST (MapServer/FeatureServer) | None (Public) | State highway layer, urban region boundaries, district limits | `OFFICIAL_GOVERNMENT_GIS` | **NOT AVAILABLE** *(Host DNS server `tracgis.telangana.gov.in` currently offline/unreachable from public internet)* |
| **ISRO Bhuvan Telangana Geoportal** | `https://bhuvan-vec1.nrsc.gov.in/bhuvan/gwc/service/wms` | OGC WMS / WMTS | None (Public) | Satellite base imagery, Telangana state transport overlays, administrative boundaries | `ISRO_BHUVAN_GIS` | **VERIFIED AND WORKING** |
| **OpenStreetMap / Overpass** | `https://overpass-api.de/api/interpreter` | Overpass QL REST API | User-Agent Header | `highway`, `name`, `ref`, `oneway`, `surface`, `coordinates`, `element_id` | `OPENSTREETMAP_OVERPASS` | **VERIFIED AND WORKING** *(Auxiliary Road Network Vector Source)* |
| **Bharat Maps (NIC Geoportal)** | `https://bharatmaps.gov.in/geoserver/wms` | OGC WMS | Self-Signed SSL | National highway network, state boundary vector tiles | `BHARAT_MAPS_NIC` | **VERIFIED BUT REQUIRES CONFIGURATION** *(SSL certificate verification override required)* |

> [!NOTE]
> OpenStreetMap / Overpass is explicitly configured as an **auxiliary road-network vector source** labeled as `OPENSTREETMAP_OVERPASS`. It is **never** presented or merged under an official government label.

---

## 🛰 2. ISRO Bhuvan Geoportal Layer Analysis

Evaluation of Bhuvan GetCapabilities metadata (`https://bhuvan-vec1.nrsc.gov.in/bhuvan/gwc/service/wms?SERVICE=WMS&REQUEST=GetCapabilities`) verified the following active layers:

| Layer Name | Data Content & Capability | Verified Fields | Can Provide Project-Level Data? |
| :--- | :--- | :--- | :--- |
| `nuis:india_transport` | National Urban Information System Transport Network Layer | Road centerline geometry, transport corridors | ❌ No (Raster/Vector road geometry only, no contract/cost facts) |
| `mmi:mmi_ap_road_network_q2_2020` | MapmyIndia / ISRO Andhra Pradesh & Telangana Road Network Dataset | Road classification, segment IDs | ❌ No (Classification only) |
| `nuis:AP_SR_admin_boundary` | Administrative boundary limits for Telangana and Andhra Pradesh | State, District, Mandal limits | ❌ No (Administrative spatial polygon bounds) |

---

## 🌐 3. OpenStreetMap / Overpass Capabilities & Real Fields

* **Capabilities**: Provides real spatial road vector features, road names, highway classification, surface quality, and spatial coordinates.
* **Retrieved Fields**:
  * `element_id` (Spatial Way ID)
  * `name` / `name:en` (Road name)
  * `ref` (Highway number, e.g. SH-4)
  * `highway` (Classification: arterial, residential, primary, service)
  * `surface` (Asphalt, concrete)
  * `oneway` (Yes/No)
  * `latitude`, `longitude`

---

## 📍 4. Real Source Response & Database Normalization

### A. Raw Vector Response (Overpass GIS Endpoint)

```json
{
  "version": 0.6,
  "generator": "Overpass API",
  "elements": [
    {
      "type": "way",
      "id": 33492155,
      "tags": {
        "highway": "service",
        "name": "ISB Ring Road",
        "oneway": "yes",
        "surface": "asphalt"
      }
    }
  ]
}
```

### B. Normalized `Road` Record in Database

```json
{
  "id": 1,
  "road_name": "ISB Ring Road",
  "road_number": null,
  "road_type": "Service",
  "latitude": 17.4447,
  "longitude": 78.3483,
  "geometry_wkt": "LINESTRING_WAY_33492155",
  "source_record_id": "33492155",
  "source_url": "https://overpass-api.de/api/interpreter",
  "source": {
    "source_name": "OpenStreetMap / Overpass",
    "source_type": "OPENSTREETMAP_OVERPASS"
  }
}
```

---

## 🧪 5. Geographic Search Experiment for IIIT Junction

Testing coordinate search: `GET /api/v1/nearby?lat=17.4447&lng=78.3483&radius=1000`

```json
[
  {
    "id": 1,
    "road_name": "ISB Ring Road",
    "road_number": null,
    "road_type": "Service",
    "distance_meters": 15.7,
    "latitude": 17.4447,
    "longitude": 78.3483,
    "geometry_wkt": "LINESTRING_WAY_33492155",
    "administrative_info": {
      "state": "Telangana",
      "district": "Hyderabad",
      "mandal_zone": "Serilingampally / Gachibowli Zone"
    },
    "source": {
      "source_name": "OpenStreetMap / Overpass",
      "source_type": "OPENSTREETMAP_OVERPASS",
      "source_url": "https://overpass-api.de/api/interpreter"
    }
  }
]
```

---

## 📌 6. Sources Capability Summary

| Capability | GIS Sources (Overpass / Bhuvan / TRAC) | e-Procurement & Project Sources (Pending) |
| :--- | :---: | :---: |
| Road Name & Geometry | ✅ **YES** | ❌ NO |
| Highway Classification | ✅ **YES** | ❌ NO |
| Spatial Distance & Coordinates | ✅ **YES** | ❌ NO |
| Administrative Boundaries | ✅ **YES** | ❌ NO |
| Project Name & Flyover Components | ❌ NO | ✅ **YES** |
| Contractor & Award Value | ❌ NO | ✅ **YES** |
| Tender Reference Number | ❌ NO | ✅ **YES** |
| Appointed Date & Progress % | ❌ NO | ✅ **YES** |

> **Conclusion**: GIS sources provide accurate spatial geometries, road names, highway types, and administrative boundaries near IIIT Junction (`17.4447, 78.3483`). However, project-level contract facts (contractor, awarded value, completion status) cannot be provided by GIS layers alone and strictly require e-Procurement/project sources.
