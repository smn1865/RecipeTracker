from app.models import Recipe, RecipeIngredient
from app.services.planner_engine import DAYS, SLOTS, select_plan_slots
import pytest


def recipe(recipe_id, title, meal_type, names):
    item = Recipe(id=recipe_id, title=title, instructions="Cook", prep_time=10, calories=400, protein_g=25, carbs_g=45, fat_g=12, meal_type=meal_type)
    item.ingredients = [RecipeIngredient(ingredient_name=name, required_qty=100, unit="g") for name in names]
    return item


def test_plan_selector_guarantees_all_21_slots_and_fallbacks():
    # No breakfast recipe is available: fallback must still fill every breakfast.
    recipes = [recipe(1, "Shared lunch", "Lunch", ["rice", "tomato"]), recipe(2, "Shared dinner", "Dinner", ["rice", "chicken"])]
    selected = select_plan_slots(recipes, {1: 2.0, 2: 2.5})
    assert len(selected) == 21
    assert {(day, slot) for day, slot, _ in selected} == {(day, slot) for day in DAYS for slot in SLOTS}
    assert all(item in recipes for _, _, item in selected)


def test_plan_selector_rewards_bulk_ingredient_reuse():
    recipes = [recipe(1, "Rice lunch", "Lunch", ["rice", "tomato"]), recipe(2, "Unique lunch", "Lunch", ["quinoa", "cucumber"]), recipe(3, "Rice dinner", "Dinner", ["rice", "chicken"])]
    selected = select_plan_slots(recipes, {1: 2.0, 2: 2.0, 3: 2.0})
    lunches = [item.id for _, slot, item in selected if slot == "Lunch"]
    assert lunches.count(1) > lunches.count(2)


def test_plan_selector_rejects_an_empty_allowed_catalog():
    with pytest.raises(ValueError, match="at least one allowed recipe"):
        select_plan_slots([], {})
