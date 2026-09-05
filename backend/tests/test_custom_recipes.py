import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.database import Base
from app.main import app
from app.models import Recipe, User
from app.routers.recipes import create_custom_recipe
from app.schemas import CustomRecipeCreate
from app.services.ai_validator import validate_custom_recipe
from app.services.location import estimated_package_cost


def valid_payload() -> dict:
    return {
        "title": "Chicken rice bowl",
        "prep_time": 25,
        "serving_count": 2,
        "total_weight_grams": 500,
        "calories": 600,
        "protein_g": 45,
        "carbs_g": 70,
        "fat_g": 16,
        "meal_type": "Dinner",
        "instructions": "Cook the rice, sear the chicken, and combine.",
        "ingredients": [
            {"ingredient_name": "Chicken breast", "grams": 220},
            {"ingredient_name": "Rice", "grams": 200},
            {"ingredient_name": "Tomato", "grams": 80},
        ],
    }


@pytest.mark.asyncio
async def test_validator_rejects_macro_calorie_mismatch(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    payload = valid_payload()
    payload["calories"] = 1800
    verdict = await validate_custom_recipe(payload)
    assert verdict["is_valid"] is False
    assert "expected approximately" in verdict["rejection_reason"]


@pytest.mark.asyncio
async def test_validator_has_deterministic_fallback_without_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert await validate_custom_recipe(valid_payload()) == {"is_valid": True, "rejection_reason": None}


def test_package_price_fallback_is_nonzero_and_weight_aware():
    small = estimated_package_cost("new ingredient", 100, "g")
    large = estimated_package_cost("new ingredient", 900, "g")
    assert small["estimated_cost"] > 0
    assert small["packages_needed"] == 1
    assert large["packages_needed"] == 2
    assert large["estimated_cost"] > small["estimated_cost"]


@pytest.mark.asyncio
async def test_valid_custom_recipe_is_persisted_as_community(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        user = User(
            email="community@example.com",
            name="Community Cook",
            password_hash="test",
            address="Yerevan, Armenia",
            lat=40.1872,
            lon=44.5152,
            height_cm=170,
            weight_kg=70,
            age=30,
            gender="other",
            activity_level="moderate",
        )
        session.add(user)
        await session.flush()
        response = await create_custom_recipe(CustomRecipeCreate(**valid_payload()), user, session)
        stored = await session.get(Recipe, response["id"], options=[selectinload(Recipe.ingredients)])
        assert stored.is_community is True
        assert stored.submitted_by_user_id == user.id
        assert len(stored.ingredients) == 3
        assert {item.ingredient_name for item in stored.ingredients} == {"chicken breast", "rice", "tomato"}
        assert await session.scalar(select(Recipe).where(Recipe.title == "Chicken rice bowl"))
    await engine.dispose()
