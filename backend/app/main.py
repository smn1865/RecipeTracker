from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import json
import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from .database import Base, engine, get_session, SessionLocal
from .models import PantryItem, Recipe, User
from .schemas import AuthResponse, GeocodeRequest, GeocodeResult, LoginRequest, NutritionProfile, OptimizeRequest, OptimizeResponse, PantryCreate, PantryOut, ProfileUpdate, RecipeFilters, RecipeSuggestion, RegisterRequest, SourcingPlanResponse, UserProfile
from .db.seed import seed
from .services.health import activity_from_assessment, bmi_status, calculate_bmi, nutrition_targets
from .services.geocoding import geocode_address
from .services.recipe_engine import shopping_plan, smart_suggestions
from .services.location import get_currency_for_coords
from .services.optimizer import optimize_basket

SECRET = "replace-me-with-an-environment-secret"
password_hash = PasswordHash.recommended()

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as connection: await connection.run_sync(Base.metadata.create_all)
    # Lightweight SQLite development migration for projects created before onboarding fields existed.
    async with engine.begin() as connection:
        existing = (await connection.exec_driver_sql("PRAGMA table_info(users)")).all()
        names = {row[1] for row in existing}
        additions = {"name": "VARCHAR(120) DEFAULT 'Pantry Member'", "address": "VARCHAR(300) DEFAULT ''", "daily_routine": "VARCHAR(48) DEFAULT 'desk'", "exercise_frequency": "VARCHAR(48) DEFAULT '0-1'", "exercise_intensity": "VARCHAR(48) DEFAULT 'light'", "daily_movement": "VARCHAR(48) DEFAULT 'under_5000'", "bmi": "FLOAT DEFAULT 0", "daily_calories": "INTEGER DEFAULT 0", "protein_target_g": "INTEGER DEFAULT 0", "carbs_target_g": "INTEGER DEFAULT 0", "fat_target_g": "INTEGER DEFAULT 0"}
        for column, sql_type in additions.items():
            if column not in names: await connection.exec_driver_sql(f"ALTER TABLE users ADD COLUMN {column} {sql_type}")
        recipes = (await connection.exec_driver_sql("PRAGMA table_info(recipes)")).all()
        recipe_columns = {row[1] for row in recipes}
        for column, sql_type in {"meal_type": "VARCHAR(32) DEFAULT 'Lunch'", "tags": "VARCHAR(255) DEFAULT 'Quick & Easy'"}.items():
            if column not in recipe_columns: await connection.exec_driver_sql(f"ALTER TABLE recipes ADD COLUMN {column} {sql_type}")
        user_profile_additions = {
            "health_goal": "VARCHAR(32) DEFAULT 'maintenance'",
            "target_calories": "INTEGER DEFAULT 0",
            "macro_preference": "VARCHAR(32) DEFAULT 'balanced'",
            "favorite_meal_ids": "TEXT DEFAULT '[]'",
            "excluded_ingredient_ids": "TEXT DEFAULT '[]'",
        }
        for column, sql_type in user_profile_additions.items():
            if column not in names:
                await connection.exec_driver_sql(f"ALTER TABLE users ADD COLUMN {column} {sql_type}")
        pantry_columns = {row[1] for row in (await connection.exec_driver_sql("PRAGMA table_info(pantry_items)")).all()}
        if "ingredient_id" not in pantry_columns:
            await connection.exec_driver_sql("ALTER TABLE pantry_items ADD COLUMN ingredient_id INTEGER")
        meal_columns = {row[1] for row in (await connection.exec_driver_sql("PRAGMA table_info(weekly_meal_assignments)")).all()}
        if "eaten" not in meal_columns:
            await connection.exec_driver_sql("ALTER TABLE weekly_meal_assignments ADD COLUMN eaten BOOLEAN DEFAULT 0")
        if "eaten_at" not in meal_columns:
            await connection.exec_driver_sql("ALTER TABLE weekly_meal_assignments ADD COLUMN eaten_at DATETIME")
    async with SessionLocal() as session: await seed(session)
    yield

app = FastAPI(title="Smart Pantry API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def issue_token(user_id: int):
    return jwt.encode({"sub": str(user_id), "exp": datetime.now(timezone.utc) + timedelta(days=7)}, SECRET, algorithm="HS256")

def refresh_health_baseline(user: User):
    user.activity_level, _ = activity_from_assessment(user.daily_routine, user.exercise_frequency, user.exercise_intensity, user.daily_movement)
    targets = nutrition_targets(user.weight_kg, user.height_cm, user.age, user.gender, user.activity_level, user.weight_goal, daily_routine=user.daily_routine, exercise_frequency=user.exercise_frequency, exercise_intensity=user.exercise_intensity, daily_movement=user.daily_movement)
    user.bmi = calculate_bmi(user.weight_kg, user.height_cm)
    user.daily_calories = user.target_calories if getattr(user, "target_calories", 0) > 0 else targets["daily_calories"]
    protein, carbs, fat = targets["protein_g"], targets["carbs_g"], targets["fat_g"]
    if getattr(user, "macro_preference", "balanced") == "high_protein":
        protein = max(protein, round(user.daily_calories * .30 / 4))
        carbs = max(0, round((user.daily_calories - protein * 4 - fat * 9) / 4))
    elif getattr(user, "macro_preference", "balanced") == "low_carb":
        carbs = round(user.daily_calories * .25 / 4)
        protein = max(protein, round(user.weight_kg * 1.8))
        fat = max(0, round((user.daily_calories - protein * 4 - carbs * 4) / 9))
    user.protein_target_g, user.carbs_target_g, user.fat_target_g = protein, carbs, fat
    targets = {"daily_calories": user.daily_calories, "protein_g": protein, "carbs_g": carbs, "fat_g": fat}
    return targets

async def current_user(authorization: str | None = Header(None), session: AsyncSession = Depends(get_session)):
    if not authorization or not authorization.startswith("Bearer "): raise HTTPException(401, "Missing bearer token")
    try: user_id = int(jwt.decode(authorization[7:], SECRET, algorithms=["HS256"])["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError): raise HTTPException(401, "Invalid token")
    user = await session.get(User, user_id)
    if not user: raise HTTPException(401, "User not found")
    return user

@app.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_session)):
    if await session.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(409, "Email already registered")
    values = payload.model_dump(exclude={"password"})
    values["favorite_meal_ids"] = json.dumps(values["favorite_meal_ids"])
    values["excluded_ingredient_ids"] = json.dumps(values["excluded_ingredient_ids"])
    user = User(**values, password_hash=password_hash.hash(payload.password))
    refresh_health_baseline(user)
    session.add(user); await session.commit(); await session.refresh(user)
    return {"access_token": issue_token(user.id), "user_id": user.id, "bmi": calculate_bmi(user.weight_kg, user.height_cm)}

@app.post("/auth/login", response_model=AuthResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)):
    user = await session.scalar(select(User).where(User.email == payload.email))
    if not user or not password_hash.verify(payload.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    return {"access_token": issue_token(user.id), "user_id": user.id, "bmi": calculate_bmi(user.weight_kg, user.height_cm)}

@app.post("/location/geocode", response_model=GeocodeResult)
async def geocode(payload: GeocodeRequest):
    return geocode_address(payload.address)

@app.get("/auth/profile", response_model=UserProfile)
async def get_profile(user: User = Depends(current_user)):
    currency, symbol, rate = get_currency_for_coords(user.lat, user.lon)
    return {"name": user.name, "age": user.age, "height_cm": user.height_cm, "weight_kg": user.weight_kg,
            "address": user.address, "lat": user.lat, "lon": user.lon, "gender": user.gender,
            "daily_routine": user.daily_routine, "exercise_frequency": user.exercise_frequency,
            "exercise_intensity": user.exercise_intensity, "daily_movement": user.daily_movement,
            "weight_goal": user.weight_goal, "health_goal": user.health_goal,
            "target_calories": user.target_calories, "macro_preference": user.macro_preference,
            "favorite_meal_ids": json.loads(user.favorite_meal_ids or "[]"),
            "excluded_ingredient_ids": json.loads(user.excluded_ingredient_ids or "[]"), "local_currency": currency,
            "local_currency_symbol": symbol, "usd_to_local_rate": rate}

@app.patch("/auth/profile", response_model=NutritionProfile)
async def update_profile(payload: ProfileUpdate, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    changes = payload.model_dump(exclude_unset=True)
    for list_field in ("favorite_meal_ids", "excluded_ingredient_ids"):
        if list_field in changes: changes[list_field] = json.dumps(changes[list_field])
    for field, value in changes.items(): setattr(user, field, value)
    if "address" in changes and "lat" not in changes and "lon" not in changes:
        point = geocode_address(user.address)
        user.address, user.lat, user.lon = point["formatted_address"], point["lat"], point["lon"]
    targets = refresh_health_baseline(user)
    await session.commit(); await session.refresh(user)
    return {"bmi": user.bmi, "weight_status": bmi_status(user.bmi), **targets, "current_weight_kg": user.weight_kg, "target_weight_kg": round(user.weight_kg * ({"deficit": .9, "surplus": 1.1}.get(user.weight_goal, 1)), 1)}

@app.get("/nutrition/profile", response_model=NutritionProfile)
async def nutrition_profile(user: User = Depends(current_user)):
    targets = refresh_health_baseline(user)
    return {"bmi": user.bmi, "weight_status": bmi_status(user.bmi), **targets, "current_weight_kg": user.weight_kg, "target_weight_kg": round(user.weight_kg * ({"deficit": .9, "surplus": 1.1}.get(user.weight_goal, 1)), 1)}

@app.get("/pantry", response_model=list[PantryOut])
async def pantry(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    return (await session.scalars(select(PantryItem).where(PantryItem.user_id == user.id).order_by(PantryItem.expiration_date.is_(None), PantryItem.expiration_date))).all()

@app.post("/pantry", response_model=PantryOut, status_code=201)
async def add_pantry_item(payload: PantryCreate, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    values = payload.model_dump()
    values["ingredient_name"] = payload.ingredient_name.lower()
    item = PantryItem(**values, user_id=user.id)
    session.add(item); await session.commit(); await session.refresh(item); return item

@app.post("/recipes/generate-smart", response_model=list[RecipeSuggestion])
async def generate_smart(filters: RecipeFilters = RecipeFilters(), user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    targets = nutrition_targets(user.weight_kg, user.height_cm, user.age, user.gender, user.activity_level, user.weight_goal, daily_routine=user.daily_routine, exercise_frequency=user.exercise_frequency, exercise_intensity=user.exercise_intensity, daily_movement=user.daily_movement)
    return await smart_suggestions(session, user, targets["daily_calories"], filters.category, filters.tag, filters.limit)

@app.get("/shopping-list/sourcing", response_model=SourcingPlanResponse)
async def sourcing(recipe_id: int = Query(gt=0), radius_km: float = Query(5, gt=0, le=50), user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    recipe = await session.get(Recipe, recipe_id, options=[selectinload(Recipe.ingredients)])
    if not recipe: raise HTTPException(404, "Recipe not found")
    pantry = (await session.scalars(select(PantryItem).where(PantryItem.user_id == user.id))).all()
    items, total = await shopping_plan(session, user, recipe, pantry, radius_km)
    currency, symbol, rate = get_currency_for_coords(getattr(user, "lat", None), getattr(user, "lon", None))
    return {"recipe_id": recipe.id, "recipe_title": recipe.title, "items": items, "total_cost": total,
            "local_currency": currency, "local_currency_symbol": symbol, "usd_to_local_rate": rate}

@app.post("/api/sourcing/optimize", response_model=OptimizeResponse)
async def optimize_sourcing(payload: OptimizeRequest, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    recipe = await session.get(Recipe, payload.recipe_id, options=[selectinload(Recipe.ingredients)])
    if not recipe: raise HTTPException(404, "Recipe not found")
    pantry = (await session.scalars(select(PantryItem).where(PantryItem.user_id == user.id))).all()
    from .services.recipe_engine import missing_for_recipe
    return await optimize_basket(session, missing_for_recipe(recipe, pantry), user.lat, user.lon, payload.distance_penalty, payload.max_stores)

from .routers.stores import router as stores_router
from .routers.planner import router as planner_router
from .routers.ingredients import router as ingredients_router
from .routers.search import router as search_router
from .routers.recipes import router as recipes_router
from .routers.pantry import router as pantry_router
from .routers.auth import router as auth_router
app.include_router(stores_router)
app.include_router(planner_router)
app.include_router(ingredients_router)
app.include_router(search_router)
app.include_router(recipes_router)
app.include_router(pantry_router)
app.include_router(auth_router)
