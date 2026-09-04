"""Key-free OpenStreetMap Nominatim geocoding with a reliable local fallback."""
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

FALLBACK_LAT = 40.1872
FALLBACK_LON = 44.5152

def fallback(address: str) -> dict:
    return {"formatted_address": address or "Default location, Yerevan", "lat": FALLBACK_LAT, "lon": FALLBACK_LON}

def geocode_address(address: str) -> dict:
    """Resolve one free-form address, returning fallback coordinates on any failure."""
    try:
        query = urlencode({"q": address, "format": "json", "limit": 1})
        request = Request(f"https://nominatim.openstreetmap.org/search?{query}", headers={"User-Agent": "SmartPantry/1.0 (location onboarding)"})
        with urlopen(request, timeout=5) as response:
            results = json.load(response)
        if not results:
            return fallback(address)
        result = results[0]
        return {"formatted_address": result.get("display_name", address), "lat": float(result["lat"]), "lon": float(result["lon"])}
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return fallback(address)
