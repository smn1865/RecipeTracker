"""Shared package-aware Armenian pricing defaults."""

from __future__ import annotations

from math import ceil
import zlib

AMD_PER_USD = 388.0

_CATEGORY_AMD_PER_KG_OR_L = {
    "produce": 950.0, "fruit": 1_100.0, "vegetable": 850.0, "grain": 900.0,
    "bakery": 1_300.0, "dairy": 1_450.0, "meat": 3_600.0, "fish": 4_400.0,
    "beverage": 700.0, "spice": 7_500.0, "packaged food": 1_650.0,
    "recipe ingredient": 1_350.0, "community": 1_350.0, "uncategorized": 1_350.0,
}

_INGREDIENT_CATEGORY_RULES = {
    "meat": ("chicken", "beef", "pork", "turkey"),
    "fish": ("salmon", "trout", "tuna", "sardine", "ishkhan"),
    "dairy": ("milk", "yogurt", "matzoon", "cheese", "butter"),
    "fruit": ("apple", "banana", "apricot", "berry", "lemon", "pomegranate"),
    "vegetable": ("tomato", "cucumber", "broccoli", "spinach", "pepper", "carrot", "potato", "onion", "pumpkin", "cabbage", "mushroom"),
    "grain": ("rice", "oat", "wheat", "bulgur", "quinoa", "pasta", "noodle", "bread", "buckwheat"),
    "spice": ("mint", "parsley", "paprika", "cinnamon", "herb"),
}

STORE_CHAINS = ("Yerevan City", "SAS", "Carrefour", "Parma", "Evrika")
STORE_PRICE_FACTORS = {"Yerevan City": .99, "SAS": 1.02, "Carrefour": 1.00, "Parma": 1.01, "Evrika": .98}

# Each entry is a real physical shopping destination.  Keeping the chain name
# separate from the branch label lets pricing remain chain-aware while distance
# calculations are always performed against the individual branch coordinates.
STORE_BRANCHES = (
    {"name": "Yerevan City", "branch_name": "Yerevan City - Abovyan", "lat": 40.1792, "lon": 44.4991, "address": "12 Abovyan St"},
    {"name": "Yerevan City", "branch_name": "Yerevan City - Mashtots", "lat": 40.1875, "lon": 44.5089, "address": "20 Mesrop Mashtots Ave"},
    {"name": "Yerevan City", "branch_name": "Yerevan City - Komitas", "lat": 40.2070, "lon": 44.5062, "address": "49 Komitas Ave"},
    {"name": "SAS", "branch_name": "SAS - Tumanyan", "lat": 40.1850, "lon": 44.5100, "address": "5 Tumanyan St"},
    {"name": "SAS", "branch_name": "SAS - Komitas", "lat": 40.2054, "lon": 44.5082, "address": "35 Komitas Ave"},
    {"name": "SAS", "branch_name": "SAS - Baghramyan", "lat": 40.1985, "lon": 44.4938, "address": "58 Marshal Baghramyan Ave"},
    {"name": "Carrefour", "branch_name": "Carrefour - Mashtots", "lat": 40.1720, "lon": 44.4920, "address": "21 Mashtots Ave"},
    {"name": "Carrefour", "branch_name": "Carrefour - Yerevan Mall", "lat": 40.1559, "lon": 44.4999, "address": "34 Arshakunyats Ave"},
    {"name": "Carrefour", "branch_name": "Carrefour - Dalma Garden", "lat": 40.1915, "lon": 44.4808, "address": "3 Tsitsernakaberd Hwy"},
    {"name": "Parma", "branch_name": "Parma - Komitas", "lat": 40.1908, "lon": 44.5156, "address": "Komitas Ave"},
    {"name": "Parma", "branch_name": "Parma - Northern Ave", "lat": 40.1828, "lon": 44.5144, "address": "8 Northern Ave"},
    {"name": "Parma", "branch_name": "Parma - Davtashen", "lat": 40.2185, "lon": 44.4815, "address": "12 Tigran Petrosyan St"},
    {"name": "Evrika", "branch_name": "Evrika - Khanjyan", "lat": 40.1818, "lon": 44.5231, "address": "Khanjyan St"},
    {"name": "Evrika", "branch_name": "Evrika - Baghramyan", "lat": 40.1947, "lon": 44.4937, "address": "60 Marshal Baghramyan Ave"},
    {"name": "Evrika", "branch_name": "Evrika - Nor Nork", "lat": 40.1983, "lon": 44.5690, "address": "15 Gai Ave"},
)


def full_street_address(address: str | None) -> str:
    address = (address or "Central Yerevan").strip()
    return address if "yerevan" in address.lower() else f"{address}, Yerevan"


def branch_name_for(store_name: str, address: str | None) -> str:
    normalized = (address or "").strip().lower()
    for branch in STORE_BRANCHES:
        if branch["name"] == store_name and branch["address"].lower() == normalized:
            return branch["branch_name"]
    street = (address or "Central").split(",", 1)[0]
    return f"{store_name} - {street}"


def unique_physical_branches(stores):
    """Discard legacy duplicate rows that point at the same chain coordinates."""
    result, seen = [], set()
    for store in stores:
        key = (store.name, round(store.lat, 5), round(store.lon, 5))
        if key not in seen:
            seen.add(key)
            result.append(store)
    return result

def store_price_factor(ingredient: str, store_name: str | None) -> float:
    """Rotate the cheapest chain per ingredient while retaining chain-level variance."""
    if store_name not in STORE_CHAINS:
        return 1.0
    winner = zlib.crc32(ingredient.strip().lower().encode("utf-8")) % len(STORE_CHAINS)
    store_index = STORE_CHAINS.index(store_name)
    rank_factor = (.86, .95, 1.00, 1.06, 1.12)[(store_index - winner) % len(STORE_CHAINS)]
    return round(STORE_PRICE_FACTORS[store_name] * rank_factor, 4)


def infer_category(ingredient: str, category: str | None = None) -> str:
    current = (category or "").strip().lower()
    if current and current not in {"uncategorized", "recipe ingredient", "community"}:
        return current
    key = ingredient.lower()
    for candidate, needles in _INGREDIENT_CATEGORY_RULES.items():
        if any(needle in key for needle in needles):
            return candidate
    return current or "uncategorized"


def base_quantity(package_size: float, unit: str) -> tuple[float, str]:
    size = max(float(package_size or 0), .0001)
    conversions = {
        "mg": (.001, "g"), "g": (1., "g"), "kg": (1000., "g"), "oz": (28.3495, "g"), "lb": (453.592, "g"),
        "ml": (1., "ml"), "cl": (10., "ml"), "l": (1000., "ml"), "pc": (1., "each"), "pcs": (1., "each"), "each": (1., "each"),
    }
    factor, base_unit = conversions.get((unit or "each").strip().lower(), (1., "each"))
    return size * factor, base_unit


def fallback_package_price_amd(ingredient: str, package_size: float, unit: str, category: str | None = None, store_name: str | None = None) -> float:
    base_size, base_unit = base_quantity(package_size, unit)
    benchmark = _CATEGORY_AMD_PER_KG_OR_L.get(infer_category(ingredient, category), _CATEGORY_AMD_PER_KG_OR_L["uncategorized"])
    total = max(180., 260. * base_size) if base_unit == "each" else benchmark * base_size / 1000.
    return round(max(120., total * store_price_factor(ingredient, store_name)), 2)


def package_quote(ingredient: str, required_qty: float, required_unit: str, *, package_size: float | None = None,
                  package_unit: str | None = None, package_price_usd: float | None = None,
                  unit_price_usd: float | None = None, category: str | None = None,
                  store_name: str | None = None) -> dict[str, float | int | str]:
    requested_base, requested_base_unit = base_quantity(required_qty, required_unit)
    selected_unit = package_unit or required_unit or "g"
    selected_size = float(package_size or (1 if selected_unit.lower() in {"each", "pc", "pcs"} else 500))
    package_base, package_base_unit = base_quantity(selected_size, selected_unit)
    if package_base_unit != requested_base_unit:
        selected_unit = required_unit or "g"
        selected_size = 1. if selected_unit.lower() in {"each", "pc", "pcs"} else (1000. if selected_unit.lower() in {"ml", "l"} else 500.)
        package_base, package_base_unit = base_quantity(selected_size, selected_unit)
    packages_needed = max(1, ceil(requested_base / max(package_base, .0001)))
    price = float(package_price_usd or 0)
    if price <= 0 and unit_price_usd and unit_price_usd > 0:
        price = float(unit_price_usd) * selected_size
    if price <= 0:
        price = fallback_package_price_amd(ingredient, selected_size, selected_unit, category, store_name) / AMD_PER_USD
    price = round(max(.01, price), 2)
    normalized_multiplier = 1000. if package_base_unit in {"g", "ml"} else 1.
    per_base_usd = price / max(package_base, .0001)
    return {"package_size": round(selected_size, 3), "package_unit": selected_unit,
            "packages_needed": packages_needed, "price_per_package_usd": price,
            "price_per_package_amd": round(price * AMD_PER_USD, 2),
            "unit_price_usd": round(per_base_usd * normalized_multiplier, 2),
            "unit_price_amd": round(per_base_usd * normalized_multiplier * AMD_PER_USD, 2),
            "normalized_unit": "kg" if package_base_unit == "g" else "L" if package_base_unit == "ml" else "each",
            "estimated_cost": round(max(.01, price * packages_needed), 2)}
