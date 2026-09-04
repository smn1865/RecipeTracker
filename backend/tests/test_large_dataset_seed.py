import httpx
import pytest

from app.db.seed_large_dataset import fetch_open_food_facts, normalize_package, parse_open_food_facts_product


def test_package_and_nutrition_normalization():
    assert normalize_package("1.5 kg") == (1.5, "kg")
    assert normalize_package("75 cl") == (750.0, "ml")
    assert normalize_package("16 oz") == (453.592, "g")
    parsed = parse_open_food_facts_product({
        "code": "123", "product_name": "Plain Yogurt", "quantity": "500 g",
        "categories_tags": ["en:dairy"],
        "nutriments": {"energy-kcal_100g": 61, "proteins_100g": 4.2, "fat_100g": 3.1, "carbohydrates_100g": 4.7},
    })
    assert parsed["name"] == "plain yogurt"
    assert parsed["barcode"] == "123"
    assert parsed["package_size"] == 500
    assert parsed["protein_g_per_100g"] == 4.2


@pytest.mark.asyncio
async def test_open_food_facts_barcode_fetch_uses_v2_endpoint():
    async def handler(request: httpx.Request):
        assert str(request.url).endswith("/api/v2/product/123.json")
        return httpx.Response(200, json={"status": 1, "product": {"code": "123", "product_name": "Lentils", "quantity": "1 kg", "nutriments": {"proteins_100g": 9}}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        rows = await fetch_open_food_facts(barcode="123", client=client)
    assert rows[0]["name"] == "lentils"
    assert rows[0]["package_unit"] == "kg"
