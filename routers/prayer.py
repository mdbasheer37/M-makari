from fastapi import APIRouter, Query, HTTPException
import httpx
import math
import logging
from datetime import datetime

router = APIRouter()
logger = logging.getLogger("makari.prayer")


def _validate_coords(lat: float, lng: float):
    if not (-90 <= lat <= 90):
        raise HTTPException(status_code=400, detail="Latitude must be between -90 and 90")
    if not (-180 <= lng <= 180):
        raise HTTPException(status_code=400, detail="Longitude must be between -180 and 180")


@router.get("/times")
async def get_prayer_times(
    lat: float = Query(...),
    lng: float = Query(...),
    method: int = Query(3, ge=0, le=23),
):
    _validate_coords(lat, lng)
    today = datetime.now().strftime("%d-%m-%Y")
    url = f"https://api.aladhan.com/v1/timings/{today}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params={"latitude": lat, "longitude": lng, "method": method})
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") == 200:
                timings = data["data"]["timings"]
                required = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha", "Sunrise", "Sunset"]
                if all(k in timings for k in required):
                    return {
                        "date": today,
                        "timings": {k: timings[k] for k in required},
                        "location": {"latitude": lat, "longitude": lng},
                        "source": "aladhan",
                    }
                logger.warning("Prayer API response missing expected timing keys")
    except httpx.TimeoutException:
        logger.warning("Prayer API request timed out")
    except httpx.HTTPError as e:
        logger.warning(f"Prayer API HTTP error: {e}")
    except (KeyError, ValueError) as e:
        logger.warning(f"Prayer API returned malformed data: {e}")
    except Exception as e:
        logger.error(f"Unexpected error fetching prayer times: {e}")

    # Fallback static times — external API unavailable
    return {
        "date": today,
        "timings": {"Fajr": "05:00", "Dhuhr": "12:30", "Asr": "15:45", "Maghrib": "18:15", "Isha": "19:45"},
        "location": {"latitude": lat, "longitude": lng},
        "source": "fallback",
        "note": "Approximate times — prayer time service is temporarily unavailable",
    }

@router.get("/qibla")
async def get_qibla(lat: float = Query(...), lng: float = Query(...)):
    _validate_coords(lat, lng)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"https://api.aladhan.com/v1/qibla/{lat}/{lng}")
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") == 200 and "direction" in data.get("data", {}):
                return {"direction": data["data"]["direction"], "latitude": lat, "longitude": lng, "source": "aladhan"}
    except httpx.TimeoutException:
        logger.warning("Qibla API request timed out")
    except httpx.HTTPError as e:
        logger.warning(f"Qibla API HTTP error: {e}")
    except (KeyError, ValueError) as e:
        logger.warning(f"Qibla API returned malformed data: {e}")
    except Exception as e:
        logger.error(f"Unexpected error fetching qibla direction: {e}")

    # Local great-circle bearing calculation — always available, no external dependency
    mecca_lat, mecca_lng = 21.4225, 39.8262
    lat_r, lng_r = math.radians(lat), math.radians(lng)
    mecca_lat_r, mecca_lng_r = math.radians(mecca_lat), math.radians(mecca_lng)
    d_lng = mecca_lng_r - lng_r
    x = math.sin(d_lng) * math.cos(mecca_lat_r)
    y = math.cos(lat_r) * math.sin(mecca_lat_r) - math.sin(lat_r) * math.cos(mecca_lat_r) * math.cos(d_lng)
    direction = (math.degrees(math.atan2(x, y)) + 360) % 360
    return {"direction": round(direction, 2), "latitude": lat, "longitude": lng, "source": "calculated"}
