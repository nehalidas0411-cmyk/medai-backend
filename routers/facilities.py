import httpx
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

router = APIRouter()

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


@router.get("/facilities")
async def find_facilities(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    radius: int = Query(5000, description="Search radius in meters", le=20000, ge=500),
    facility_type: Optional[str] = Query(None, description="Filter by type: hospital, clinic, pharmacy, laboratory")
):
    # Build Overpass QL query
    amenity_filter = "hospital|clinic|doctors|pharmacy|laboratory|nursing_home|healthcare"
    if facility_type == "hospital":    amenity_filter = "hospital"
    elif facility_type == "clinic":    amenity_filter = "clinic|doctors"
    elif facility_type == "pharmacy":  amenity_filter = "pharmacy"
    elif facility_type == "laboratory": amenity_filter = "laboratory"

    query = f"""[out:json][timeout:25];
(
  node["amenity"~"{amenity_filter}"](around:{radius},{lat},{lng});
  way["amenity"~"{amenity_filter}"](around:{radius},{lat},{lng});
  relation["amenity"~"{amenity_filter}"](around:{radius},{lat},{lng});
);
out center;"""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(OVERPASS_URL, content=query)
            resp.raise_for_status()
            data = resp.json()

        facilities = []
        for elem in data.get("elements", []):
            tags = elem.get("tags", {})
            if not tags.get("name"):
                continue  # skip unnamed facilities

            # Get coordinates
            if elem["type"] == "node":
                flat, flng = elem.get("lat"), elem.get("lon")
            else:
                center = elem.get("center", {})
                flat, flng = center.get("lat"), center.get("lon")

            if not flat or not flng:
                continue

            facilities.append({
                "name":     tags.get("name", "Unknown"),
                "amenity":  tags.get("amenity", "healthcare"),
                "address":  " ".join(filter(None, [
                    tags.get("addr:housenumber", ""),
                    tags.get("addr:street", ""),
                    tags.get("addr:city", ""),
                ])) or None,
                "phone":    tags.get("phone") or tags.get("contact:phone"),
                "website":  tags.get("website") or tags.get("contact:website"),
                "opening_hours": tags.get("opening_hours"),
                "lat": flat,
                "lng": flng,
            })

        # Sort by distance
        def haversine(lat1, lng1, lat2, lng2):
            from math import radians, sin, cos, sqrt, atan2
            R = 6371000
            f1, f2 = radians(lat1), radians(lat2)
            df = radians(lat2 - lat1)
            dl = radians(lng2 - lng1)
            a = sin(df/2)**2 + cos(f1)*cos(f2)*sin(dl/2)**2
            return R * 2 * atan2(sqrt(a), sqrt(1-a))

        for f in facilities:
            f["distance_m"] = round(haversine(lat, lng, f["lat"], f["lng"]))

        facilities.sort(key=lambda x: x["distance_m"])
        return {"count": len(facilities), "facilities": facilities[:50]}

    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Map service error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
