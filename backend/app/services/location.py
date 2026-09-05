from math import asin, ceil, cos, radians, sin, sqrt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Ingredient, LocalStore, StoreInventoryItem, StorePrice
from .catalog import STORE_CHAINS, branch_name_for, full_street_address, package_quote, unique_physical_branches

FALLBACK_LAT, FALLBACK_LON = 40.1872, 44.5152
BASE_PRICES = {"egg": .10, "chicken breast": .009, "brown rice": .003, "broccoli": .004,
               "oats": .002, "greek yogurt": .006, "banana": .002, "salmon": .018,
               "tofu": .006, "lentils": .003, "tuna": .012, "tomato": .003}
DEFAULT_PACKAGES = {"g": 500.0, "kg": .5, "ml": 1000.0, "l": 1.0, "oz": 16.0, "lb": 1.0, "each": 6.0}
DEFAULT_UNIT_PRICES = {"g": .005, "kg": 5.0, "ml": .002, "l": 2.0, "oz": .15, "lb": 3.5, "each": .75}


def estimated_package_cost(
    ingredient: str,
    qty: float,
    unit: str,
    package_size: float | None = None,
    unit_price: float | None = None,
    price_factor: float = 1.0,
    category: str | None = None,
    store_name: str | None = None,
) -> dict:
    """Return a positive, unit-normalized package quote for any ingredient."""
    normalized_unit = (unit or "g").strip().lower()
    selected_size = package_size if package_size and package_size > 0 else DEFAULT_PACKAGES.get(normalized_unit, 1.0)
    quote = package_quote(
        ingredient,
        max(float(qty), 0.0001),
        normalized_unit,
        package_size=selected_size,
        package_unit=normalized_unit,
        unit_price_usd=(unit_price * price_factor) if unit_price and unit_price > 0 else None,
        category=category,
        store_name=store_name,
    )
    return quote

def user_coordinates(lat: float | None, lon: float | None) -> tuple[float, float]:
    """Return saved coordinates when valid, otherwise the application's free local fallback."""
    if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return FALLBACK_LAT, FALLBACK_LON
    return lat, lon

def active_user_coordinates(header_lat: float | None, header_lon: float | None,
                            saved_lat: float | None, saved_lon: float | None) -> tuple[float, float]:
    """Prefer valid live client coordinates, then saved profile coordinates, then Yerevan."""
    if header_lat is not None and header_lon is not None and -90 <= header_lat <= 90 and -180 <= header_lon <= 180:
        return header_lat, header_lon
    return user_coordinates(saved_lat, saved_lon)

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
    estimate = estimated_package_cost(ingredient, qty, unit)
    return {"store_name": "Local Supermarket", "address": "Central neighborhood market",
            "distance_km": 1.2, **estimate}

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
    stores = unique_physical_branches((await session.scalars(select(LocalStore))).all())
    return [(s, distance_km(lat, lon, s.lat, s.lon)) for s in stores if s.name in STORE_CHAINS and distance_km(lat, lon, s.lat, s.lon) <= radius_km]

async def options_for_ingredient(session: AsyncSession, ingredient: str, qty: float, unit: str, lat: float, lon: float, radius_km: float = 5):
    lat, lon = user_coordinates(lat, lon)
    candidates = []
    try:
        for store, distance in await nearby_stores(session, lat, lon, radius_km):
            price = await session.scalar(select(StorePrice).where(StorePrice.store_id == store.id, StorePrice.ingredient_name == ingredient.lower(), StorePrice.unit == unit))
            inventory = await session.scalar(select(StoreInventoryItem).where(
                StoreInventoryItem.store_id == store.id,
                StoreInventoryItem.ingredient_name == ingredient.lower(),
                StoreInventoryItem.unit == unit,
            ))
            if inventory and not inventory.in_stock:
                continue
            canonical = await session.scalar(select(Ingredient).where(Ingredient.name == ingredient.lower()))
            package_size = (
                inventory.package_size if inventory and inventory.package_size > 0
                else canonical.package_size if canonical and canonical.package_unit == unit and canonical.package_size
                else None
            )
            factor = .90 + (sum(ord(char) for char in f"{store.id}:{ingredient}") % 21) / 100
            estimate = estimated_package_cost(
                ingredient,
                qty,
                unit,
                package_size=package_size,
                unit_price=price.price_per_unit if price else None,
                price_factor=factor,
                category=canonical.category if canonical else None,
                store_name=store.name,
            )
            if inventory and inventory.price_usd > 0:
                estimate["price_per_package_usd"] = round(inventory.price_usd, 2)
                inventory_quote = package_quote(ingredient, qty, unit, package_size=inventory.package_size,
                                                package_unit=inventory.unit, package_price_usd=inventory.price_usd,
                                                category=canonical.category if canonical else None, store_name=store.name)
                estimate.update(inventory_quote)
                estimate["estimated_cost"] = round(max(.01, estimate["packages_needed"] * inventory.price_usd), 2)
            candidates.append({"store_name": store.name, "branch_name": branch_name_for(store.name, store.address),
                               "street_address": full_street_address(store.address), "address": store.address,
                               "distance_km": distance, **estimate})
    except Exception:
        # Sourcing is advisory; an unavailable local catalog must never block meal planning.
        candidates = []
    if not candidates:
        return generated_neighborhood_options(ingredient, qty, unit)
    ordered=sorted(candidates, key=lambda x: (x["estimated_cost"], x["distance_km"]))
    distinct=[];seen_chains=set()
    for option in ordered:
        if option["store_name"] in seen_chains: continue
        seen_chains.add(option["store_name"]);distinct.append(option)
        if len(distinct)==3: break
    return distinct
