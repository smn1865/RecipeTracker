"""High-throughput ingredient/recipe ingestion and local-price generation.

Examples:
    python -m app.db.seed_large_dataset --ingredients ingredients.jsonl \
        --recipes recipes.csv --generate-prices
    python -m app.db.seed_large_dataset --off-barcode 3017620422003

For 100k+ records, JSON Lines or CSV avoids loading the whole source into memory.
All inserts use SQLAlchemy executemany batches rather than per-row ORM flushes.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import insert, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from ..database import Base
from ..models import Ingredient, LocalStore, Recipe, RecipeIngredient, StoreInventoryItem, StorePrice
from ..services.catalog import AMD_PER_USD, STORE_BRANCHES, fallback_package_price_amd

OFF_PRODUCT_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
DEFAULT_BATCH_SIZE = 5_000
STORE_FIXTURES = [
    {key: value for key, value in branch.items() if key != "branch_name"}
    for branch in STORE_BRANCHES
]


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def normalize_package(value: Any, unit: Any = None) -> tuple[float | None, str | None]:
    """Return a numeric package and a canonical g/ml/kg/each unit."""
    raw = str(value or "").strip().lower()
    unit_raw = str(unit or "").strip().lower()
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*(kg|g|mg|l|cl|ml|oz|lb|each|pc|pcs)?", raw)
    if match:
        size = _number(match.group(1))
        parsed_unit = match.group(2) or unit_raw
    elif value not in (None, ""):
        size, parsed_unit = _number(value), unit_raw
    else:
        return None, None
    aliases = {"grams": "g", "gram": "g", "kilograms": "kg", "kilogram": "kg", "litre": "l", "liter": "l", "pc": "each", "pcs": "each"}
    parsed_unit = aliases.get(parsed_unit, parsed_unit)
    if parsed_unit == "mg":
        return round(size / 1000, 4), "g"
    if parsed_unit == "l":
        return round(size * 1000, 4), "ml"
    if parsed_unit == "cl":
        return round(size * 10, 4), "ml"
    if parsed_unit == "oz":
        return round(size * 28.3495, 4), "g"
    if parsed_unit == "lb":
        return round(size * 453.592, 4), "g"
    return (round(size, 4), parsed_unit) if parsed_unit in {"g", "ml", "kg", "each"} else (round(size, 4), "g")


def parse_open_food_facts_product(product: dict[str, Any]) -> dict[str, Any] | None:
    name = (product.get("product_name") or product.get("product_name_en") or "").strip()
    if not name:
        return None
    size, package_unit = normalize_package(
        product.get("quantity") or product.get("product_quantity"),
        product.get("product_quantity_unit"),
    )
    nutriments = product.get("nutriments") or {}
    categories = product.get("categories_tags") or product.get("categories") or []
    if isinstance(categories, str):
        categories = [item.strip() for item in categories.split(",") if item.strip()]
    category = str(categories[0]).removeprefix("en:").replace("-", " ") if categories else "packaged food"
    return {
        "name": name.lower()[:120],
        "category": category[:80],
        "barcode": str(product.get("code") or product.get("_id") or "").strip() or None,
        "package_size": size,
        "package_unit": package_unit,
        "calories_per_100g": _number(nutriments.get("energy-kcal_100g", nutriments.get("energy-kcal", 0))),
        "protein_g_per_100g": _number(nutriments.get("proteins_100g", 0)),
        "fat_g_per_100g": _number(nutriments.get("fat_100g", 0)),
        "carbs_g_per_100g": _number(nutriments.get("carbohydrates_100g", 0)),
        "fiber_g_per_100g": _number(nutriments.get("fiber_100g", 0)),
    }


async def fetch_open_food_facts(
    *, barcode: str | None = None, query: str | None = None, limit: int = 25,
    client: httpx.AsyncClient | None = None,
) -> list[dict[str, Any]]:
    """Fetch and normalize Open Food Facts products by barcode or search text."""
    if not barcode and not query:
        raise ValueError("barcode or query is required")
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=15, headers={"User-Agent": "BariAkhorzhakSeeder/1.0 (data-import)"})
    try:
        if barcode:
            response = await client.get(OFF_PRODUCT_URL.format(barcode=barcode))
            response.raise_for_status()
            payload = response.json()
            products = [payload.get("product", {})] if payload.get("status") == 1 else []
        else:
            response = await client.get(OFF_SEARCH_URL, params={"search_terms": query, "search_simple": 1, "action": "process", "json": 1, "page_size": min(limit, 100)})
            response.raise_for_status()
            products = response.json().get("products", [])[:limit]
        parsed = [parse_open_food_facts_product(product) for product in products]
        return [item for item in parsed if item]
    finally:
        if owns_client:
            await client.aclose()


def _stream_json_array(path: Path, chunk_size: int = 1 << 20) -> Iterator[dict[str, Any]]:
    decoder, buffer, position, eof = json.JSONDecoder(), "", 0, False
    with path.open(encoding="utf-8") as handle:
        while True:
            if not eof and len(buffer) - position < chunk_size // 2:
                buffer = buffer[position:] + handle.read(chunk_size)
                position = 0
                eof = len(buffer) < chunk_size
            while position < len(buffer) and buffer[position] in " \t\r\n[,": position += 1
            if position < len(buffer) and buffer[position] == "]": return
            if position >= len(buffer):
                if eof: return
                continue
            try:
                value, position = decoder.raw_decode(buffer, position)
                if isinstance(value, dict): yield value
            except json.JSONDecodeError:
                if eof: raise
                buffer = buffer[position:] + handle.read(chunk_size)
                position = 0
                eof = len(buffer) < chunk_size


def iter_source(path: str | Path, collection: str | None = None) -> Iterator[dict[str, Any]]:
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix in {".csv", ".tsv"}:
        with source.open(newline="", encoding="utf-8-sig") as handle:
            yield from csv.DictReader(handle, delimiter="\t" if suffix == ".tsv" else ",")
        return
    if suffix in {".jsonl", ".ndjson"}:
        with source.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip(): yield json.loads(line)
        return
    if suffix == ".json":
        with source.open(encoding="utf-8") as handle:
            first = next((char for char in iter(lambda: handle.read(1), "") if not char.isspace()), "")
        if first == "[":
            yield from _stream_json_array(source)
        else:
            payload = json.loads(source.read_text(encoding="utf-8"))
            records = payload.get(collection or "items", payload) if isinstance(payload, dict) else payload
            yield from records
        return
    raise ValueError(f"Unsupported source format: {source.suffix}")


def batches(records: Iterable[dict[str, Any]], size: int) -> Iterator[list[dict[str, Any]]]:
    batch: list[dict[str, Any]] = []
    for record in records:
        batch.append(record)
        if len(batch) >= size:
            yield batch; batch = []
    if batch: yield batch


def ingredient_mapping(record: dict[str, Any]) -> dict[str, Any] | None:
    if "nutriments" in record or "product_name" in record:
        return parse_open_food_facts_product(record)
    name = str(record.get("name") or record.get("ingredient_name") or "").strip()
    if not name: return None
    size, unit = normalize_package(record.get("package_size") or record.get("quantity"), record.get("package_unit") or record.get("unit"))
    return {
        "name": name.lower()[:120],
        "category": str(record.get("category") or "uncategorized").lower()[:80],
        "barcode": str(record.get("barcode") or "").strip() or None,
        "package_size": size,
        "package_unit": unit,
        "calories_per_100g": _number(record.get("calories_per_100g", record.get("calories", 0))),
        "protein_g_per_100g": _number(record.get("protein_g_per_100g", record.get("protein_g", record.get("protein", 0)))),
        "fat_g_per_100g": _number(record.get("fat_g_per_100g", record.get("fat_g", record.get("fat", 0)))),
        "carbs_g_per_100g": _number(record.get("carbs_g_per_100g", record.get("carbs_g", record.get("carbs", 0)))),
        "fiber_g_per_100g": _number(record.get("fiber_g_per_100g", record.get("fiber_g", record.get("fiber", 0)))),
    }


def _recipe_ingredients(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, str):
        try: value = json.loads(value)
        except json.JSONDecodeError:
            value = [{"name":parts[0],"quantity":parts[1],"unit":parts[2]} for token in value.split(";") if len(parts := token.split(":")) >= 3]
    result=[]
    for item in value or []:
        if isinstance(item, (list,tuple)) and len(item)>=3: name,quantity,unit=item[:3]
        else: name=item.get("name") or item.get("ingredient_name");quantity=item.get("quantity") or item.get("required_qty");unit=item.get("unit")
        if name and _number(quantity)>0 and unit: result.append({"ingredient_name":str(name).strip().lower()[:120],"required_qty":_number(quantity),"unit":str(unit).strip()[:32]})
    return result


def recipe_mapping(record: dict[str, Any]) -> tuple[dict[str, Any],list[dict[str, Any]]] | None:
    title=str(record.get("title") or record.get("name") or "").strip()
    if not title:return None
    instructions=record.get("instructions") or record.get("steps") or ""
    if isinstance(instructions,list): instructions=" ".join(f"{index}. {step}" for index,step in enumerate(instructions,1))
    tags=record.get("tags") or "Budget Friendly"
    if isinstance(tags,list):tags=",".join(map(str,tags))
    row={"title":title[:255],"instructions":str(instructions),"prep_time":int(_number(record.get("prep_time",record.get("prep_time_minutes",20)),20)),"calories":int(_number(record.get("calories",0))),"protein_g":_number(record.get("protein_g",record.get("protein",0))),"carbs_g":_number(record.get("carbs_g",record.get("carbs",0))),"fat_g":_number(record.get("fat_g",record.get("fat",0))),"meal_type":str(record.get("meal_type") or record.get("category") or "Lunch")[:32],"tags":str(tags)[:255]}
    return row,_recipe_ingredients(record.get("ingredients"))


async def bulk_insert_ingredients(session: AsyncSession, records: Iterable[dict[str, Any]], batch_size: int=DEFAULT_BATCH_SIZE) -> int:
    existing_names={value.lower() for value in (await session.scalars(select(Ingredient.name))).all()};existing_barcodes={value for value in (await session.scalars(select(Ingredient.barcode))).all() if value};inserted=0
    for source_batch in batches(records,batch_size):
        rows=[]
        for record in source_batch:
            row=ingredient_mapping(record)
            if not row or row["name"] in existing_names or (row["barcode"] and row["barcode"] in existing_barcodes):continue
            existing_names.add(row["name"])
            if row["barcode"]:existing_barcodes.add(row["barcode"])
            rows.append(row)
        if rows: await session.execute(insert(Ingredient),rows);await session.commit();inserted+=len(rows)
    return inserted


async def bulk_insert_recipes(session: AsyncSession, records: Iterable[dict[str, Any]], batch_size: int=DEFAULT_BATCH_SIZE) -> tuple[int,int]:
    existing_titles=set((await session.scalars(select(Recipe.title))).all());recipe_count=ingredient_count=0
    for source_batch in batches(records,batch_size):
        parsed=[];batch_titles=set()
        for record in source_batch:
            item=recipe_mapping(record)
            if item and item[0]["title"] not in existing_titles and item[0]["title"] not in batch_titles:
                parsed.append(item);batch_titles.add(item[0]["title"])
        if not parsed:continue
        rows=[item[0] for item in parsed]
        returned=(await session.execute(insert(Recipe).returning(Recipe.id,Recipe.title),rows)).all();ids={title:recipe_id for recipe_id,title in returned}
        links=[];ingredient_names=[]
        for row,ingredients in parsed:
            existing_titles.add(row["title"])
            for item in ingredients:links.append({"recipe_id":ids[row["title"]],**item});ingredient_names.append(item["ingredient_name"])
        if links:await session.execute(insert(RecipeIngredient),links)
        await session.commit();recipe_count+=len(rows);ingredient_count+=len(links)
        await bulk_insert_ingredients(session,({"name":name,"category":"recipe ingredient"} for name in dict.fromkeys(ingredient_names)),batch_size)
    return recipe_count,ingredient_count


async def ensure_local_stores(session: AsyncSession) -> list[LocalStore]:
    existing={(store.name,store.address):store for store in (await session.scalars(select(LocalStore))).all()}
    for fixture in STORE_FIXTURES:
        key=(fixture["name"],fixture["address"])
        if key not in existing:
            store=LocalStore(**fixture);session.add(store);existing[key]=store
        else:
            existing[key].lat=fixture["lat"];existing[key].lon=fixture["lon"]
    await session.commit()
    return [existing[(item["name"],item["address"])] for item in STORE_FIXTURES]


def _base_package_amd(category: str, package_size: float, unit: str) -> float:
    return fallback_package_price_amd("generic ingredient", package_size, unit, category)


async def generate_local_store_prices(session: AsyncSession,batch_size: int=DEFAULT_BATCH_SIZE,usd_to_amd: float=AMD_PER_USD) -> tuple[int,int]:
    stores=await ensure_local_stores(session);ingredients=(await session.execute(select(Ingredient.name,Ingredient.category,Ingredient.package_size,Ingredient.package_unit))).all()
    price_rows={(row.store_id,row.ingredient_name,row.unit):row for row in (await session.scalars(select(StorePrice))).all()}
    inventory_rows={(row.store_id,row.ingredient_name,row.unit):row for row in (await session.scalars(select(StoreInventoryItem))).all()}
    prices=[];inventory=[];price_count=inventory_count=0
    for name,category,package_size,package_unit in ingredients:
        unit=package_unit or "g";size=package_size or (1 if unit=="each" else 500)
        for index,store in enumerate(stores):
            package_amd=fallback_package_price_amd(name,size,unit,category,store.name)
            package_usd=round(max(.01,package_amd/usd_to_amd),2);amd_per_unit=round(package_amd/max(size,1e-9),4);usd_per_unit=round(max(.000001,amd_per_unit/usd_to_amd),6)
            key=(store.id,name,unit)
            if key not in price_rows:prices.append({"store_id":store.id,"ingredient_name":name,"price_per_unit":usd_per_unit,"price_amd_per_unit":amd_per_unit,"unit":unit})
            elif price_rows[key].price_per_unit<=0 or price_rows[key].price_amd_per_unit<=0:
                price_rows[key].price_per_unit,price_rows[key].price_amd_per_unit=usd_per_unit,amd_per_unit
            if key not in inventory_rows:inventory.append({"store_id":store.id,"ingredient_name":name,"package_size":size,"unit":unit,"price_usd":package_usd,"price_amd":package_amd,"in_stock":True})
            else:
                current=inventory_rows[key]
                if current.price_usd<=0:current.price_usd=package_usd
                if current.price_amd<=0:current.price_amd=package_amd
            if len(prices)>=batch_size:await session.execute(insert(StorePrice),prices);await session.commit();price_count+=len(prices);prices=[]
            if len(inventory)>=batch_size:await session.execute(insert(StoreInventoryItem),inventory);await session.commit();inventory_count+=len(inventory);inventory=[]
    if prices:await session.execute(insert(StorePrice),prices);price_count+=len(prices)
    if inventory:await session.execute(insert(StoreInventoryItem),inventory);inventory_count+=len(inventory)
    await session.commit();return price_count,inventory_count


async def prepare_database(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        if connection.dialect.name=="sqlite":
            columns={row[1] for row in (await connection.exec_driver_sql("PRAGMA table_info(ingredients)")).all()}
            for name,definition in {"category":"VARCHAR(80) DEFAULT 'uncategorized'","barcode":"VARCHAR(64)","package_size":"FLOAT","package_unit":"VARCHAR(12)"}.items():
                if name not in columns:await connection.exec_driver_sql(f"ALTER TABLE ingredients ADD COLUMN {name} {definition}")
            price_columns={row[1] for row in (await connection.exec_driver_sql("PRAGMA table_info(store_prices)")).all()}
            if "price_amd_per_unit" not in price_columns:await connection.exec_driver_sql("ALTER TABLE store_prices ADD COLUMN price_amd_per_unit FLOAT DEFAULT 0")
            inventory_columns={row[1] for row in (await connection.exec_driver_sql("PRAGMA table_info(store_inventory_items)")).all()}
            if "price_amd" not in inventory_columns:await connection.exec_driver_sql("ALTER TABLE store_inventory_items ADD COLUMN price_amd FLOAT DEFAULT 0")
        elif connection.dialect.name=="postgresql":
            await connection.execute(text("ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS category VARCHAR(80) DEFAULT 'uncategorized'"))
            await connection.execute(text("ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS barcode VARCHAR(64)"))
            await connection.execute(text("ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS package_size DOUBLE PRECISION"))
            await connection.execute(text("ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS package_unit VARCHAR(12)"))
            await connection.execute(text("ALTER TABLE store_prices ADD COLUMN IF NOT EXISTS price_amd_per_unit DOUBLE PRECISION DEFAULT 0"))
            await connection.execute(text("ALTER TABLE store_inventory_items ADD COLUMN IF NOT EXISTS price_amd DOUBLE PRECISION DEFAULT 0"))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS ix_ingredients_name ON ingredients (name)"))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS ix_ingredients_category ON ingredients (category)"))
        await connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_ingredients_barcode ON ingredients (barcode)"))


async def run_pipeline(args: argparse.Namespace) -> dict[str,int]:
    engine=create_async_engine(args.database_url);await prepare_database(engine);factory=async_sessionmaker(engine,expire_on_commit=False,class_=AsyncSession);stats={"ingredients":0,"recipes":0,"recipe_ingredients":0,"store_prices":0,"inventory_items":0}
    async with factory() as session:
        if args.ingredients:stats["ingredients"]+=await bulk_insert_ingredients(session,iter_source(args.ingredients,"ingredients"),args.batch_size)
        if args.recipes:stats["recipes"],stats["recipe_ingredients"]=await bulk_insert_recipes(session,iter_source(args.recipes,"recipes"),args.batch_size)
        off=[]
        async with httpx.AsyncClient(timeout=15,headers={"User-Agent":"BariAkhorzhakSeeder/1.0 (data-import)"}) as client:
            for barcode in args.off_barcode or []:off.extend(await fetch_open_food_facts(barcode=barcode,client=client))
            if args.off_query:off.extend(await fetch_open_food_facts(query=args.off_query,limit=args.off_limit,client=client))
        if off:stats["ingredients"]+=await bulk_insert_ingredients(session,off,args.batch_size)
        if args.generate_prices:stats["store_prices"],stats["inventory_items"]=await generate_local_store_prices(session,args.batch_size,args.usd_to_amd)
    await engine.dispose();return stats


def build_parser() -> argparse.ArgumentParser:
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--ingredients");parser.add_argument("--recipes");parser.add_argument("--database-url",default=os.getenv("DATABASE_URL","sqlite+aiosqlite:///./smart_pantry.db"));parser.add_argument("--batch-size",type=int,default=DEFAULT_BATCH_SIZE);parser.add_argument("--generate-prices",action="store_true");parser.add_argument("--usd-to-amd",type=float,default=AMD_PER_USD);parser.add_argument("--off-barcode",action="append");parser.add_argument("--off-query");parser.add_argument("--off-limit",type=int,default=25);return parser


if __name__=="__main__":
    result=asyncio.run(run_pipeline(build_parser().parse_args()))
    print(json.dumps(result,indent=2))
