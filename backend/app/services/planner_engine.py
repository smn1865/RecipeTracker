from ..models import Recipe

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
SLOTS = ["Breakfast", "Lunch", "Dinner"]


def select_plan_slots(recipes: list[Recipe], recipe_costs: dict[int, float]) -> list[tuple[str, str, Recipe]]:
    """Fill all 21 slots, favoring shared ingredients while allowing safe repeats."""
    if not recipes:
        raise ValueError("at least one allowed recipe is required")
    by_slot = {slot: [recipe for recipe in recipes if (recipe.meal_type or "").lower() == slot.lower()] for slot in SLOTS}
    chosen: list[tuple[str, str, Recipe]] = []
    used_counts: dict[str, int] = {}
    repeats: dict[int, int] = {}
    fallback = sorted(recipes, key=lambda recipe: (recipe_costs.get(recipe.id, float("inf")), recipe.id))
    for day in DAYS:
        for slot in SLOTS:
            candidates = by_slot[slot] or fallback
            def score(recipe: Recipe):
                names = {item.ingredient_name.lower() for item in recipe.ingredients}
                overlap = sum(used_counts.get(name, 0) for name in names) / max(1, len(names))
                overlap_discount = min(.72, overlap * .22)
                base_cost = recipe_costs.get(recipe.id, float("inf"))
                repeat_penalty = repeats.get(recipe.id, 0) * max(.05, base_cost * .04)
                return (base_cost * (1 - overlap_discount) + repeat_penalty, recipe.id)
            selected = min(candidates, key=score)
            chosen.append((day, slot, selected))
            repeats[selected.id] = repeats.get(selected.id, 0) + 1
            for ingredient in selected.ingredients:
                name = ingredient.ingredient_name.lower()
                used_counts[name] = used_counts.get(name, 0) + 1
    if len(chosen) != len(DAYS) * len(SLOTS):
        raise RuntimeError("weekly planner failed to fill all meal slots")
    return chosen
