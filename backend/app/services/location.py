from math import asin, cos, radians, sin, sqrt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import LocalStore, StorePrice

FALLBACK_LAT, FALLBACK_LON = 40.1872, 44.5152
BASE_PRICES = {"egg": .10, "chicken breast": .009, "brown rice": .003, "broccoli": .004,
               "oats": .002, "greek yogurt": .006, "banana": .002, "salmon": .018,
               "tofu": .006, "lentils": .003, "tuna": .012, "tomato": .003}

def user_coordinates(lat: float | None, lon: float | None) -> tuple[float, float]:
    """Return saved coordinates when valid, otherwise the application's free local fallback."""
    if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return FALLBACK_LAT, FALLBACK_LON
    return lat, lon

def get_currency_for_coords(lat: float | None, lon: float | None) -> tuple[str, str, float]:
    """Free coordinate heuristic for display currency; source prices remain USD estimates."""
    lat, lon = user_coordinates(lat, lon)
    if 38.8 <= lat <= 41.3 and 43.4 <= lon <= 46.6:
        return "AMD", "֏", 388.0
    if 35.0 <= lat <= 70.0 and -10.0 <= lon <= 30.0:
        return "EUR", "€", 0.92
    return "USD", "$", 1.0

def fallback_option(ingredient: str, qty: float, unit: str) -> dict:
    """Local heuristic used when a price feed/database record is unavailable."""
    unit_price = BASE_PRICES.get(ingredient.lower(), .005 if unit == "g" else .75)
    return {"store_name": "Local Supermarket", "address": "Central neighborhood market",
            "distance_km": 1.2, "estimated_cost": round(max(0, qty) * unit_price, 2)}

def generated_neighborhood_options(ingredient: str, qty: float, unit: str) -> list[dict]:
    """Free local-store heuristic when no catalog entries are nearby."""
    base = fallback_option(ingredient, qty, unit)
    choices = [("City Market", "Main Street neighborhood", 0.8, .96),
               ("Local Supermarket", "Central neighborhood market", 1.2, 1),
               ("Local Farmers Market", "Community market square", 2.1, 1.08)]
    return [{"store_name": name, "address": address, "distance_km": distance,
             "estimated_cost": round(base["estimated_cost"] * multiplier, 2)} for name, address, distance, multiplier in choices]

def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance; replace store lookup with Google Places in a production adapter."""
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return round(6371 * 2 * asin(sqrt(a)), 2)

async def nearby_stores(session: AsyncSession, lat: float, lon: float, radius_km: float = 5):
    stores = (await session.scalars(select(LocalStore))).all()
    return [(s, distance_km(lat, lon, s.lat, s.lon)) for s in stores if distance_km(lat, lon, s.lat, s.lon) <= radius_km]

async def options_for_ingredient(session: AsyncSession, ingredient: str, qty: float, unit: str, lat: float, lon: float, radius_km: float = 5):
    lat, lon = user_coordinates(lat, lon)
    candidates = []
    try:
        for store, distance in await nearby_stores(session, lat, lon, radius_km):
            price = await session.scalar(select(StorePrice).where(StorePrice.store_id == store.id, StorePrice.ingredient_name == ingredient.lower(), StorePrice.unit == unit))
            if price:
                candidates.append({"store_name": store.name, "address": store.address, "distance_km": distance,
                                   "estimated_cost": round(price.price_per_unit * qty, 2)})
    except Exception:
        # Sourcing is advisory; an unavailable local catalog must never block meal planning.
        candidates = []
    if not candidates:
        return generated_neighborhood_options(ingredient, qty, unit)
    return sorted(candidates, key=lambda x: (x["estimated_cost"], x["distance_km"]))
