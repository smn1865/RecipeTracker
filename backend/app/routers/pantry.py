from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..main import current_user
from ..models import Ingredient, PantryItem, User
from ..schemas import PantryItemCreate, PantryItemResponse, PantryItemUpdate

router = APIRouter(prefix="/api/pantry", tags=["pantry"])


def pantry_response(item: PantryItem) -> dict:
    return {
        "id": item.id,
        "ingredient_id": item.ingredient_id,
        "ingredient_name": item.ingredient_name,
        "quantity": item.quantity,
        "unit": item.unit,
        "expiration_date": item.expiration_date,
    }


@router.get("", response_model=list[PantryItemResponse])
async def list_pantry(
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    items = (await session.scalars(
        select(PantryItem)
        .where(PantryItem.user_id == user.id, PantryItem.quantity > 0)
        .order_by(PantryItem.expiration_date.is_(None), PantryItem.expiration_date, PantryItem.ingredient_name)
    )).all()
    changed = False
    for item in items:
        if item.ingredient_id is None:
            ingredient = await session.scalar(
                select(Ingredient).where(func.lower(Ingredient.name) == item.ingredient_name.lower())
            )
            if ingredient:
                item.ingredient_id = ingredient.id
                changed = True
    if changed:
        await session.commit()
    return [pantry_response(item) for item in items if item.ingredient_id is not None]


@router.post("/items", response_model=PantryItemResponse, status_code=status.HTTP_201_CREATED)
async def create_pantry_item(
    payload: PantryItemCreate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    ingredient = await session.get(Ingredient, payload.ingredient_id)
    if not ingredient:
        raise HTTPException(404, "Ingredient not found")
    item = PantryItem(
        user_id=user.id,
        ingredient_id=ingredient.id,
        ingredient_name=ingredient.name.lower(),
        quantity=payload.quantity,
        unit=payload.unit.strip(),
        expiration_date=payload.expiration_date,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return pantry_response(item)


@router.patch("/items/{item_id}", response_model=PantryItemResponse)
async def update_pantry_item(
    item_id: int,
    payload: PantryItemUpdate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    item = await session.scalar(
        select(PantryItem).where(PantryItem.id == item_id, PantryItem.user_id == user.id)
    )
    if not item:
        raise HTTPException(404, "Pantry item not found")
    if payload.remove:
        item.quantity = 0
    else:
        changes = payload.model_dump(exclude_unset=True, exclude={"remove"})
        for field, value in changes.items():
            setattr(item, field, value)
    await session.commit()
    await session.refresh(item)
    return pantry_response(item)
