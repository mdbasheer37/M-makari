from fastapi import APIRouter, Query
import httpx
from datetime import datetime

router = APIRouter()

@router.get("/times")
async def get_prayer_times(
    lat: float = Query(...),
    lng: float = Query(...),
    method: int = Query(3)
):
    today = datetime.now().strftime("%d-%m-%Y")
    url = f"http://api.aladhan.com/v1/timings/{today}?latitude={lat}&longitude={lng}&method={method}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            data = resp.json()
            if data.get("code") == 200:
                timings = data["data"]["timings"]
                return {
                    "date": today,
                    "timings": {
                        "Fajr": timings["Fajr"],
                        "Dhuhr": timings["Dhuhr"],
                        "Asr": timings["Asr"],
                        "Maghrib": timings["Maghrib"],
                        "Isha": timings["Isha"],
                        "Sunrise": timings["Sunrise"],
                        "Sunset": timings["Sunset"],
                    },
                    "location": {"latitude": lat, "longitude": lng}
                }
    except Exception as e:
        pass
    # Fallback static times
    return {
        "date": today,
        "timings": {"Fajr": "05:00", "Dhuhr": "12:30", "Asr": "15:45", "Maghrib": "18:15", "Isha": "19:45"},
        "note": "Approximate times - enable location for accurate times"
    }

@router.get("/qibla")
async def get_qibla(lat: float = Query(...), lng: float = Query(...)):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"http://api.aladhan.com/v1/qibla/{lat}/{lng}")
            data = resp.json()
            if data.get("code") == 200:
                return {"direction": data["data"]["direction"], "latitude": lat, "longitude": lng}
    except:
        pass
    import math
    mecca_lat, mecca_lng = 21.4225, 39.8262
    lat_r, lng_r = math.radians(lat), math.radians(lng)
    mecca_lat_r, mecca_lng_r = math.radians(mecca_lat), math.radians(mecca_lng)
    d_lng = mecca_lng_r - lng_r
    x = math.sin(d_lng) * math.cos(mecca_lat_r)
    y = math.cos(lat_r) * math.sin(mecca_lat_r) - math.sin(lat_r) * math.cos(mecca_lat_r) * math.cos(d_lng)
    direction = (math.degrees(math.atan2(x, y)) + 360) % 360
    return {"direction": round(direction, 2), "latitude": lat, "longitude": lng}
