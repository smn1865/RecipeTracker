from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..main import current_user, refresh_health_baseline
from ..models import Ingredient, Recipe, User
from ..schemas import DietaryPreferencesResponse, DietaryPreferencesUpdate
from ..services.preferences import encode_ids, id_list

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/onboarding-options")
async def onboarding_options(session: AsyncSession = Depends(get_session)):
    recipes = (await session.scalars(select(Recipe).order_by(Recipe.meal_type, Recipe.title))).all()
    ingredients = (await session.scalars(select(Ingredient).order_by(Ingredient.name))).all()
    return {
        "recipes": [{"id": item.id, "title": item.title, "meal_type": item.meal_type} for item in recipes],
        "ingredients": [{"id": item.id, "name": item.name} for item in ingredients],
    }


def response(user: User) -> dict:
    return {
        "health_goal": user.health_goal,
        "weight_goal": user.weight_goal,
        "target_calories": user.target_calories,
        "macro_preference": user.macro_preference,
        "favorite_meal_ids": id_list(user.favorite_meal_ids),
        "excluded_ingredient_ids": id_list(user.excluded_ingredient_ids),
    }


@router.get("/preferences", response_model=DietaryPreferencesResponse)
async def get_preferences(user: User = Depends(current_user)):
    return response(user)


@router.patch("/preferences", response_model=DietaryPreferencesResponse)
async def update_preferences(
    payload: DietaryPreferencesUpdate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    changes = payload.model_dump(exclude_unset=True)
    for list_field in ("favorite_meal_ids", "excluded_ingredient_ids"):
        if list_field in changes:
            changes[list_field] = encode_ids(changes[list_field])
    for field, value in changes.items():
        setattr(user, field, value)
    refresh_health_baseline(user)
    if user.target_calories > 0:
        user.daily_calories = user.target_calories
    await session.commit()
    await session.refresh(user)
    return response(user)
