import json

from ..models import Recipe, User


def id_list(value: str | list[int] | None) -> list[int]:
    if isinstance(value, list):
        return [int(item) for item in value]
    try:
        decoded = json.loads(value or "[]")
        return [int(item) for item in decoded] if isinstance(decoded, list) else []
    except (TypeError, ValueError, json.JSONDecodeError):
        return []


def encode_ids(values: list[int] | None) -> str:
    return json.dumps(sorted(set(int(item) for item in (values or []))))


def recipe_is_allowed(recipe: Recipe, excluded_ingredient_ids: set[int], ingredient_ids_by_name: dict[str, int]) -> bool:
    return not any(
        ingredient_ids_by_name.get(item.ingredient_name.strip().lower()) in excluded_ingredient_ids
        for item in recipe.ingredients
    )


def user_excluded_ids(user: User) -> set[int]:
    return set(id_list(user.excluded_ingredient_ids))
