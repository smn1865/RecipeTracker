from datetime import date, datetime
from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), default="Pantry Member")
    password_hash: Mapped[str] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(String(300), default="")
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    height_cm: Mapped[float] = mapped_column(Float)
    weight_kg: Mapped[float] = mapped_column(Float)
    age: Mapped[int] = mapped_column(Integer)
    gender: Mapped[str] = mapped_column(String(32))
    activity_level: Mapped[str] = mapped_column(String(32))
    daily_routine: Mapped[str] = mapped_column(String(48), default="desk")
    exercise_frequency: Mapped[str] = mapped_column(String(48), default="0-1")
    exercise_intensity: Mapped[str] = mapped_column(String(48), default="light")
    daily_movement: Mapped[str] = mapped_column(String(48), default="under_5000")
    weight_goal: Mapped[str] = mapped_column(String(32), default="maintenance")
    bmi: Mapped[float] = mapped_column(Float, default=0)
    daily_calories: Mapped[int] = mapped_column(Integer, default=0)
    protein_target_g: Mapped[int] = mapped_column(Integer, default=0)
    carbs_target_g: Mapped[int] = mapped_column(Integer, default=0)
    fat_target_g: Mapped[int] = mapped_column(Integer, default=0)
    pantry_items: Mapped[list["PantryItem"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class PantryItem(Base):
    __tablename__ = "pantry_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    ingredient_name: Mapped[str] = mapped_column(String(120), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(32))
    expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    user: Mapped[User] = relationship(back_populates="pantry_items")

class Recipe(Base):
    __tablename__ = "recipes"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    instructions: Mapped[str] = mapped_column(Text)
    prep_time: Mapped[int] = mapped_column(Integer)
    calories: Mapped[int] = mapped_column(Integer)
    protein_g: Mapped[float] = mapped_column(Float)
    carbs_g: Mapped[float] = mapped_column(Float)
    fat_g: Mapped[float] = mapped_column(Float)
    meal_type: Mapped[str] = mapped_column(String(32), default="Lunch", index=True)
    tags: Mapped[str] = mapped_column(String(255), default="Quick & Easy")
    ingredients: Mapped[list["RecipeIngredient"]] = relationship(back_populates="recipe", cascade="all, delete-orphan")

class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"
    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), index=True)
    ingredient_name: Mapped[str] = mapped_column(String(120), index=True)
    required_qty: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(32))
    recipe: Mapped[Recipe] = relationship(back_populates="ingredients")

class Ingredient(Base):
    __tablename__ = "ingredients"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    calories_per_100g: Mapped[float] = mapped_column(Float, default=0)
    protein_g_per_100g: Mapped[float] = mapped_column(Float, default=0)
    fat_g_per_100g: Mapped[float] = mapped_column(Float, default=0)
    carbs_g_per_100g: Mapped[float] = mapped_column(Float, default=0)
    fiber_g_per_100g: Mapped[float] = mapped_column(Float, default=0)

class LocalStore(Base):
    __tablename__ = "local_stores"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    address: Mapped[str] = mapped_column(String(255))
    prices: Mapped[list["StorePrice"]] = relationship(back_populates="store", cascade="all, delete-orphan")

class StorePrice(Base):
    __tablename__ = "store_prices"
    __table_args__ = (UniqueConstraint("store_id", "ingredient_name", "unit"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("local_stores.id"), index=True)
    ingredient_name: Mapped[str] = mapped_column(String(120), index=True)
    price_per_unit: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(32))
    store: Mapped[LocalStore] = relationship(back_populates="prices")

class StoreInventoryItem(Base):
    __tablename__ = "store_inventory_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("local_stores.id"), index=True)
    ingredient_name: Mapped[str] = mapped_column(String(120), index=True)
    package_size: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(12))
    price_usd: Mapped[float] = mapped_column(Float)
    in_stock: Mapped[bool] = mapped_column(default=True)

class StoreItemReport(Base):
    __tablename__ = "store_item_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("store_inventory_items.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    report_type: Mapped[str] = mapped_column(String(16))
    reported_price_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

class WeeklyMealAssignment(Base):
    __tablename__ = "weekly_meal_assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    day: Mapped[str] = mapped_column(String(12))
    slot: Mapped[str] = mapped_column(String(16))
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"))
