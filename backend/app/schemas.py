from datetime import date
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8)
    address: str = Field(min_length=6, max_length=300)
    lat: float = Field(default=40.1872, ge=-90, le=90)
    lon: float = Field(default=44.5152, ge=-180, le=180)
    height_cm: float = Field(gt=50, le=300)
    weight_kg: float = Field(gt=15, le=500)
    age: int = Field(ge=13, le=120)
    gender: str
    activity_level: str = "moderate"
    daily_routine: str
    exercise_frequency: str
    exercise_intensity: str
    daily_movement: str
    weight_goal: str = "maintenance"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class GeocodeRequest(BaseModel):
    address: str = Field(min_length=6, max_length=300)

class GeocodeResult(BaseModel):
    formatted_address: str
    lat: float
    lon: float

class AuthResponse(BaseModel):
    access_token: str
    user_id: int
    bmi: float

class PantryCreate(BaseModel):
    ingredient_name: str
    quantity: float = Field(gt=0)
    unit: str
    expiration_date: date | None = None

class PantryOut(PantryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int

class NutritionProfile(BaseModel):
    bmi: float
    weight_status: str
    daily_calories: int
    protein_g: int
    carbs_g: int
    fat_g: int
    current_weight_kg: float
    target_weight_kg: float

class ProfileUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=120)
    age: int | None = Field(None, ge=13, le=120)
    height_cm: float | None = Field(None, gt=50, le=300)
    weight_kg: float | None = Field(None, gt=15, le=500)
    address: str | None = Field(None, min_length=6, max_length=300)
    lat: float | None = Field(None, ge=-90, le=90)
    lon: float | None = Field(None, ge=-180, le=180)
    daily_routine: str | None = None
    exercise_frequency: str | None = None
    exercise_intensity: str | None = None
    daily_movement: str | None = None
    weight_goal: str | None = None

class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    age: int
    height_cm: float
    weight_kg: float
    address: str
    lat: float
    lon: float
    gender: str
    daily_routine: str
    exercise_frequency: str
    exercise_intensity: str
    daily_movement: str
    weight_goal: str
    local_currency: str
    local_currency_symbol: str
    usd_to_local_rate: float

class IngredientNeed(BaseModel):
    ingredient_name: str
    quantity: float
    unit: str

class RecipeSuggestion(BaseModel):
    id: int
    title: str
    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    prep_time: int
    meal_type: str
    tags: list[str]
    pantry_match_percent: float
    missing_ingredients: list[IngredientNeed]
    estimated_missing_cost: float

class RecipeFilters(BaseModel):
    category: str = "All"
    tag: str | None = None
    limit: int = Field(default=12, ge=1, le=24)

class StoreOption(BaseModel):
    store_name: str
    address: str
    distance_km: float
    estimated_cost: float

class ShoppingItem(BaseModel):
    ingredient_name: str
    quantity: float
    unit: str
    best_option: StoreOption
    alternatives: list[StoreOption] = []

class ShoppingPlan(BaseModel):
    recipe_id: int
    recipe_title: str
    items: list[ShoppingItem]
    total_cost: float

class SourcingPlanResponse(ShoppingPlan):
    local_currency: str
    local_currency_symbol: str
    usd_to_local_rate: float

class OptimizeRequest(BaseModel):
    recipe_id: int = Field(gt=0)
    distance_penalty: float = Field(default=.15, ge=0, le=10)
    max_stores: int = Field(default=3, ge=1, le=3)

class StoreAssignment(BaseModel):
    store_name: str
    address: str
    distance_km: float
    items: list[IngredientNeed]
    item_cost: float

class OptimizeResponse(BaseModel):
    single_store_total: float
    optimized_total: float
    travel_distance_km: float
    net_savings: float
    uses_multi_store: bool
    assignments: list[StoreAssignment]

class PriceReport(BaseModel):
    price_usd: float = Field(gt=0)

class StockReport(BaseModel):
    out_of_stock: bool = True

class InventoryItemOut(BaseModel):
    id: int
    ingredient_name: str
    package_size: float
    unit: str
    price_usd: float
    unit_price_usd: float
    unit_price_local: float
    in_stock: bool

class MealAssignmentIn(BaseModel):
    day: str
    slot: str
    recipe_id: int

class ConsolidateRequest(BaseModel):
    assignments: list[MealAssignmentIn]
    weekly_budget: float = Field(gt=0)

class ConsolidateResponse(BaseModel):
    total_cost: float
    weekly_budget: float
    exceeds_budget: bool
    missing_ingredients: list[IngredientNeed]
    swap_suggestions: list[str]
