from app.models import Ingredient, Recipe, RecipeIngredient
from app.services.preferences import encode_ids, id_list, recipe_is_allowed


def test_preference_id_lists_are_stable_and_unique():
    assert encode_ids([3, 1, 3]) == "[1, 3]"
    assert id_list("[1, 3]") == [1, 3]
    assert id_list("not json") == []


def test_excluded_ingredient_is_a_strict_recipe_guardrail():
    oats = Ingredient(id=7, name="oats")
    recipe = Recipe(title="Oat bowl", instructions="Mix", prep_time=3, calories=300, protein_g=12, carbs_g=45, fat_g=8)
    recipe.ingredients = [RecipeIngredient(ingredient_name="oats", required_qty=50, unit="g")]
    assert not recipe_is_allowed(recipe, {oats.id}, {"oats": oats.id})
    assert recipe_is_allowed(recipe, set(), {"oats": oats.id})
