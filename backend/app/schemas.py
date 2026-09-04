from datetime import date, datetime
from typing import Literal
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

class PantryItemCreate(BaseModel):
    ingredient_id: int = Field(gt=0)
    quantity: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=32)
    expiration_date: date | None = None

class PantryItemUpdate(BaseModel):
    quantity: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, min_length=1, max_length=32)
    expiration_date: date | None = None
    remove: bool = False

class PantryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ingredient_id: int
    ingredient_name: str
    quantity: float
    unit: str
    expiration_date: date | None = None

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

class AutoGenerateRequest(BaseModel):
    weekly_budget: float | None = Field(default=None, gt=0)

class PlannedMeal(BaseModel):
    meal_id: int
    day: str
    slot: str
    recipe_id: int
    title: str
    estimated_cost_usd: float
    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    eaten: bool = False
    eaten_at: datetime | None = None

class ConsolidateResponse(BaseModel):
    total_cost: float
    weekly_budget: float
    exceeds_budget: bool
    missing_ingredients: list[IngredientNeed]
    swap_suggestions: list[str]
    meals: list[PlannedMeal] = Field(default_factory=list)

class AggregatedIngredient(BaseModel):
    ingredient_name: str
    quantity: float
    unit: str
    estimated_cost_usd: float

class AutoGenerateResponse(BaseModel):
    meals: list[PlannedMeal]
    total_cost_usd: float
    total_cost_local: float
    local_currency: str
    local_currency_symbol: str
    usd_to_local_rate: float
    saved_via_overlap_usd: float
    ingredients: list[AggregatedIngredient]
    total_calories: int
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    weekly_budget: float | None
    exceeds_budget: bool

class IngredientNutrition(BaseModel):
    id: int
    name: str
    calories_per_100g: float
    protein_g_per_100g: float
    fat_g_per_100g: float
    carbs_g_per_100g: float
    fiber_g_per_100g: float

class IngredientStoreOption(BaseModel):
    store_id: int
    store_name: str
    address: str
    distance_km: float
    price_usd: float
    price_local: float
    unit: str
    in_stock: bool
    navigation_url: str

class IngredientStoresResponse(BaseModel):
    ingredient: IngredientNutrition
    suggested_recipe_id: int | None = None
    suggested_recipe_title: str | None = None
    local_currency: str
    local_currency_symbol: str
    usd_to_local_rate: float
    stores: list[IngredientStoreOption]

class SearchDishResult(BaseModel):
    id: int
    title: str
    meal_type: str
    estimated_cost_usd: float
    calories: int

class SearchIngredientResult(BaseModel):
    id: int
    name: str
    estimated_cost_usd: float
    unit: str

class UnifiedSearchResponse(BaseModel):
    dishes: list[SearchDishResult]
    ingredients: list[SearchIngredientResult]

class RecipeIngredientStorePrice(BaseModel):
    store_id: int
    store_name: str
    address: str
    distance_km: float
    package_size: float
    package_unit: str
    packages_needed: int
    price_per_package_usd: float
    extended_price_usd: float
    extended_price_local: float
    in_stock: bool
    navigation_url: str

class RecipeIngredientSourcing(BaseModel):
    ingredient_id: int | None = None
    ingredient_name: str
    required_quantity: float
    pantry_quantity: float
    missing_quantity: float
    coverage_status: Literal["FULLY_OWNED", "PARTIALLY_OWNED", "MISSING"]
    unit: str
    store_options: list[RecipeIngredientStorePrice]

class IngredientUsage(BaseModel):
    ingredient_id: int = Field(gt=0)
    used_amount: float = Field(gt=0)
    unit: str | None = None

class MealConsumeRequest(BaseModel):
    used_default_quantities: bool = True
    custom_ingredient_usage: list[IngredientUsage] = Field(default_factory=list)

class MealConsumeResponse(BaseModel):
    meal_id: int
    eaten: bool
    eaten_at: datetime
    pantry_items: list[PantryItemResponse]

class MealStoreChoice(BaseModel):
    store_id: int
    store_name: str
    address: str
    distance_km: float
    item_total_usd: float
    total_with_travel_usd: float
    navigation_url: str

class MealSplitStore(BaseModel):
    store_id: int
    store_name: str
    address: str
    distance_km: float
    item_total_usd: float
    navigation_url: str
    ingredients: list[str]

class MealMultiStoreChoice(BaseModel):
    stores: list[MealSplitStore]
    item_total_usd: float
    travel_penalty_usd: float
    total_with_travel_usd: float
    savings_vs_single_usd: float

class RecipeSourcingResponse(BaseModel):
    recipe_id: int
    recipe_title: str
    ingredients: list[RecipeIngredientSourcing]
    total_estimated_cost_usd: float
    total_estimated_cost_local: float
    local_currency: str
    local_currency_symbol: str
    usd_to_local_rate: float
    best_single_store: MealStoreChoice | None
    multi_store_split: MealMultiStoreChoice | None
