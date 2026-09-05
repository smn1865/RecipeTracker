from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_session
from ..main import current_user
from ..models import StoreInventoryItem, StoreItemReport, User
from ..schemas import InventoryItemOut, PriceReport, StockReport
from ..services.location import estimated_package_cost, get_currency_for_coords
from ..services.catalog import package_quote

router = APIRouter(prefix="/api/stores", tags=["stores"])

def normalized_price(item: StoreInventoryItem, rate: float):
    quote = package_quote(item.ingredient_name, item.package_size, item.unit,
                          package_size=item.package_size, package_unit=item.unit,
                          package_price_usd=item.price_usd)
    if item.price_usd <= 0:
        item.price_usd = quote["price_per_package_usd"]
        item.price_amd = quote["price_per_package_amd"]
    usd = quote["unit_price_usd"]
    return usd, round(usd * rate, 2)

@router.post("/items/{item_id}/report-price", response_model=InventoryItemOut)
async def report_price(item_id: int, payload: PriceReport, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    item = await session.get(StoreInventoryItem, item_id)
    if not item: raise HTTPException(404, "Inventory item not found")
    item.price_usd = payload.price_usd
    item.price_amd = round(payload.price_usd * 388.0, 2)
    session.add(StoreItemReport(item_id=item_id, user_id=user.id, report_type="price", reported_price_usd=payload.price_usd))
    await session.commit(); await session.refresh(item)
    _, _, rate = get_currency_for_coords(user.lat, user.lon); usd, local = normalized_price(item, rate)
    return {"id":item.id,"ingredient_name":item.ingredient_name,"package_size":item.package_size,"unit":item.unit,"price_usd":max(.01,item.price_usd),"unit_price_usd":usd,"unit_price_local":local,"in_stock":item.in_stock}

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
    return {"id":item.id,"ingredient_name":item.ingredient_name,"package_size":item.package_size,"unit":item.unit,"price_usd":max(.01,item.price_usd),"unit_price_usd":usd,"unit_price_local":local,"in_stock":item.in_stock}
