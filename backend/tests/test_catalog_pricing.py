from types import SimpleNamespace

from app.services.catalog import STORE_BRANCHES, STORE_CHAINS, base_quantity, branch_name_for, fallback_package_price_amd, package_quote, unique_physical_branches
from app.services.optimizer import choose_store_tradeoff


def test_weight_and_volume_packages_normalize_to_base_units():
    assert base_quantity(1.5, "kg") == (1500.0, "g")
    assert base_quantity(16, "oz") == (453.592, "g")
    assert base_quantity(1, "L") == (1000.0, "ml")


def test_fallback_quotes_are_positive_and_store_specific():
    evrika = fallback_package_price_amd("chicken breast", 500, "g", store_name="Evrika")
    sas = fallback_package_price_amd("chicken breast", 500, "g", store_name="SAS")
    assert evrika > 0
    assert sas > evrika
    quote = package_quote("unknown pantry item", 1200, "g", package_size=500, package_unit="g", package_price_usd=0)
    assert quote["packages_needed"] == 3
    assert quote["estimated_cost"] > 0
    assert quote["normalized_unit"] == "kg"


def test_price_rotation_distributes_winning_chains():
    ingredients=("tomato","chicken","rice","yogurt","salmon","lentils","oats","apple","cheese","bread")
    winners={min(STORE_CHAINS,key=lambda store:fallback_package_price_amd(item,500,"g",store_name=store)) for item in ingredients}
    assert len(winners)>=3


def test_branch_catalog_has_multiple_locations_and_removes_legacy_coordinate_duplicates():
    assert len(STORE_BRANCHES) >= 15
    assert branch_name_for("Parma", "Komitas Ave") == "Parma - Komitas"
    stores = [
        SimpleNamespace(name="Parma", lat=40.1908, lon=44.5156),
        SimpleNamespace(name="Parma", lat=40.1908, lon=44.5156),
        SimpleNamespace(name="Parma", lat=40.1828, lon=44.5144),
    ]
    assert len(unique_physical_branches(stores)) == 2


def test_farther_store_requires_material_savings():
    candidates = [
        {"store_id": 1, "store_name": "Nearby", "address": "A", "distance_km": 1.0, "item_total_usd": 12.0, "navigation_url": "near"},
        {"store_id": 2, "store_name": "Value", "address": "B", "distance_km": 3.5, "item_total_usd": 9.0, "navigation_url": "far"},
    ]
    closest, value = choose_store_tradeoff(candidates)
    assert closest["store_name"] == "Nearby"
    assert value["store_name"] == "Value"
    assert value["savings_usd"] == 2.62
    assert value["price_savings_usd"] == 3.0
    assert value["extra_distance_km"] == 2.5
    assert "Worth the Trip" in value["badge_label"]

    candidates[1]["item_total_usd"] = 11.0
    _, value = choose_store_tradeoff(candidates)
    assert value is None
