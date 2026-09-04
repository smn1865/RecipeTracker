import pytest

from app.models import Ingredient, PantryItem, RecipeIngredient
from app.services.recipe_matcher import convert_quantity, recipe_coverage


def test_compatible_unit_conversion():
    assert convert_quantity(1, "kg", "g") == 1000
    assert round(convert_quantity(16, "oz", "g"), 1) == 453.6
    assert convert_quantity(1, "each", "g") is None


@pytest.mark.asyncio
async def test_recipe_coverage_reports_full_partial_and_missing():
    ingredients = [Ingredient(id=1, name="oats"), Ingredient(id=2, name="banana"), Ingredient(id=3, name="egg")]

    class Result:
        def all(self):
            return ingredients

    class Session:
        async def scalars(self, _statement):
            return Result()

    requirements = [
        RecipeIngredient(ingredient_name="oats", required_qty=400, unit="g"),
        RecipeIngredient(ingredient_name="banana", required_qty=100, unit="g"),
        RecipeIngredient(ingredient_name="egg", required_qty=2, unit="each"),
    ]
    pantry = [
        PantryItem(ingredient_id=1, ingredient_name="oats", quantity=.5, unit="kg"),
        PantryItem(ingredient_id=2, ingredient_name="banana", quantity=50, unit="g"),
    ]
    rows = await recipe_coverage(Session(), requirements, pantry)

    assert [row["coverage_status"] for row in rows] == ["FULLY_OWNED", "PARTIALLY_OWNED", "MISSING"]
    assert rows[0]["missing_quantity"] == 0
    assert rows[1]["missing_quantity"] == 50
    assert rows[2]["missing_quantity"] == 2
