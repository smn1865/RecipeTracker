from app.db.seed import EXTRA_RECIPES
from app.seed import RECIPES


def test_expanded_catalog_has_exact_requirements_and_armenian_staples():
    catalog = RECIPES + EXTRA_RECIPES
    assert len(catalog) >= 50
    titles = {recipe[0] for recipe in catalog}
    assert {"Spas Yogurt Soup", "Ghapama Stuffed Pumpkin", "Lean Khorovats Plate", "Harissa Chicken Porridge", "Baked Ishkhan with Herbs"} <= titles
    for title, instructions, _prep, calories, protein, carbs, fat, _meal, _tags, ingredients in catalog:
        assert calories > 0 and protein >= 0 and carbs >= 0 and fat >= 0, title
        assert ingredients and all(quantity > 0 and unit for _name, quantity, unit in ingredients), title
        if title in titles - {recipe[0] for recipe in RECIPES}:
            assert "1." in instructions and "2." in instructions and "3." in instructions, title
