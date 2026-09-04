from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_session
from ..main import current_user
from ..models import StoreInventoryItem, StoreItemReport, User
from ..schemas import InventoryItemOut, PriceReport, StockReport
from ..services.location import get_currency_for_coords

router = APIRouter(prefix="/api/stores", tags=["stores"])

def normalized_price(item: StoreInventoryItem, rate: float):
    multiplier = {"kg": 1, "g": 1000, "lb": 2.20462, "oz": 35.274, "L": 1, "ml": 1000}.get(item.unit, 1)
    usd = round(item.price_usd / max(item.package_size, .001) * multiplier, 4)
    return usd, round(usd * rate, 2)

@router.post("/items/{item_id}/report-price", response_model=InventoryItemOut)
async def report_price(item_id: int, payload: PriceReport, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    item = await session.get(StoreInventoryItem, item_id)
    if not item: raise HTTPException(404, "Inventory item not found")
    item.price_usd = payload.price_usd
    session.add(StoreItemReport(item_id=item_id, user_id=user.id, report_type="price", reported_price_usd=payload.price_usd))
    await session.commit(); await session.refresh(item)
    _, _, rate = get_currency_for_coords(user.lat, user.lon); usd, local = normalized_price(item, rate)
    return {"id":item.id,"ingredient_name":item.ingredient_name,"package_size":item.package_size,"unit":item.unit,"price_usd":item.price_usd,"unit_price_usd":usd,"unit_price_local":local,"in_stock":item.in_stock}

@router.post("/items/{item_id}/report-stock", response_model=InventoryItemOut)
async def report_stock(item_id: int, payload: StockReport, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    item = await session.get(StoreInventoryItem, item_id)
    if not item: raise HTTPException(404, "Inventory item not found")
    if payload.out_of_stock:
        session.add(StoreItemReport(item_id=item_id, user_id=user.id, report_type="stock"))
        await session.flush()
        count = await session.scalar(select(func.count()).select_from(StoreItemReport).where(StoreItemReport.item_id==item_id, StoreItemReport.report_type=="stock", StoreItemReport.created_at >= datetime.utcnow()-timedelta(hours=24)))
        item.in_stock = count < 2
    await session.commit(); await session.refresh(item)
    _, _, rate = get_currency_for_coords(user.lat, user.lon); usd, local = normalized_price(item, rate)
    return {"id":item.id,"ingredient_name":item.ingredient_name,"package_size":item.package_size,"unit":item.unit,"price_usd":item.price_usd,"unit_price_usd":usd,"unit_price_local":local,"in_stock":item.in_stock}
