from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import LocalStore, Recipe, RecipeIngredient, StorePrice

RECIPES = [
 ("Berry Yogurt Oats", "Stir oats into yogurt and top with banana.", 5, 410, 26, 58, 9, "Breakfast", "High Protein,Quick & Easy,Budget Friendly", [("oats",70,"g"),("greek yogurt",200,"g"),("banana",120,"g")]),
 ("Broccoli Egg Scramble", "Steam broccoli and scramble with eggs.", 12, 320, 25, 12, 20, "Breakfast", "High Protein,Quick & Easy", [("egg",3,"each"),("broccoli",100,"g")]),
 ("Peanut Banana Toast", "Toast bread and layer peanut butter and banana.", 6, 380, 14, 48, 17, "Breakfast", "Quick & Easy,Budget Friendly", [("bread",80,"g"),("banana",100,"g"),("peanut butter",30,"g")]),
 ("Veggie Omelet", "Cook vegetables then fold into beaten eggs.", 15, 350, 27, 18, 19, "Breakfast", "High Protein,Vegetarian", [("egg",3,"each"),("spinach",80,"g"),("tomato",100,"g")]),
 ("Protein Chicken Bowl", "Cook rice. Sear chicken and steam broccoli.", 25, 560, 48, 60, 14, "Lunch", "High Protein,Meal Prep", [("chicken breast",180,"g"),("brown rice",100,"g"),("broccoli",120,"g")]),
 ("Chickpea Garden Bowl", "Toss chickpeas, rice and fresh vegetables.", 15, 470, 18, 74, 12, "Lunch", "Vegetarian,Budget Friendly", [("chickpeas",160,"g"),("brown rice",90,"g"),("tomato",100,"g")]),
 ("Tuna Crunch Wrap", "Fill a wrap with tuna, spinach and yogurt sauce.", 10, 430, 36, 45, 11, "Lunch", "High Protein,Quick & Easy", [("tuna",120,"g"),("bread",80,"g"),("spinach",60,"g"),("greek yogurt",40,"g")]),
 ("Lentil Soup", "Simmer lentils with tomatoes and seasoning.", 30, 390, 22, 60, 7, "Lunch", "Vegetarian,Budget Friendly", [("lentils",150,"g"),("tomato",150,"g"),("bread",50,"g")]),
 ("Salmon Rice Plate", "Bake salmon and serve with rice and broccoli.", 28, 590, 42, 55, 20, "Dinner", "High Protein", [("salmon",160,"g"),("brown rice",100,"g"),("broccoli",120,"g")]),
 ("Turkey Tomato Pasta", "Cook pasta and toss with turkey and tomato.", 25, 560, 41, 65, 14, "Dinner", "High Protein,Quick & Easy", [("turkey",150,"g"),("pasta",110,"g"),("tomato",140,"g")]),
 ("Tofu Stir Fry", "Sauté tofu, broccoli and rice.", 20, 490, 28, 56, 18, "Dinner", "Vegetarian,Quick & Easy", [("tofu",180,"g"),("broccoli",150,"g"),("brown rice",90,"g")]),
 ("Chicken Taco Plate", "Season chicken and build tacos with beans.", 25, 610, 47, 64, 17, "Dinner", "High Protein", [("chicken breast",170,"g"),("black beans",130,"g"),("bread",80,"g"),("tomato",100,"g")]),
 ("Bean & Veggie Chili", "Simmer beans, tomatoes and lentils.", 35, 440, 23, 71, 8, "Dinner", "Vegetarian,Budget Friendly", [("black beans",150,"g"),("lentils",100,"g"),("tomato",180,"g")]),
 ("Greek Yogurt Parfait", "Layer yogurt, banana and oats.", 4, 280, 20, 38, 5, "Snack", "High Protein,Quick & Easy,Budget Friendly", [("greek yogurt",180,"g"),("banana",80,"g"),("oats",25,"g")]),
 ("Hummus Toast", "Spread hummus over warm toast with tomato.", 7, 310, 12, 42, 12, "Snack", "Vegetarian,Budget Friendly", [("hummus",70,"g"),("bread",70,"g"),("tomato",70,"g")]),
 ("Apple Peanut Bites", "Slice apple and serve with peanut butter.", 3, 260, 8, 34, 12, "Snack", "Quick & Easy,Budget Friendly", [("apple",160,"g"),("peanut butter",25,"g")]),
 ("Tuna Cucumber Cups", "Fill cucumber rounds with tuna yogurt mix.", 8, 220, 29, 10, 8, "Snack", "High Protein,Quick & Easy", [("tuna",100,"g"),("cucumber",150,"g"),("greek yogurt",50,"g")]),
 ("Banana Oat Smoothie", "Blend yogurt, banana and oats until smooth.", 5, 340, 21, 56, 5, "Snack", "Quick & Easy,Vegetarian", [("banana",120,"g"),("greek yogurt",150,"g"),("oats",35,"g")]),
]

async def seed(session: AsyncSession):
    stores = (await session.scalars(select(LocalStore))).all()
    if not stores:
        stores = [LocalStore(name="Green Basket",lat=40.1792,lon=44.4991,address="12 Abovyan St"), LocalStore(name="Fresh Market",lat=40.1850,lon=44.5100,address="5 Tumanyan St"), LocalStore(name="Value Grocer",lat=40.1720,lon=44.4920,address="21 Mashtots Ave")]
        session.add_all(stores); await session.flush()
    prices={"chicken breast":.009,"brown rice":.003,"broccoli":.004,"egg":.10,"oats":.002,"greek yogurt":.006,"banana":.002,"bread":.003,"peanut butter":.008,"spinach":.004,"tomato":.003,"chickpeas":.003,"tuna":.012,"lentils":.003,"salmon":.018,"turkey":.011,"pasta":.0025,"tofu":.006,"black beans":.003,"hummus":.007,"apple":.0025,"cucumber":.002}
    existing_prices={(p.store_id,p.ingredient_name) for p in (await session.scalars(select(StorePrice))).all()}
    for ingredient,base in prices.items():
        unit="each" if ingredient=="egg" else "g"
        for index,store in enumerate(stores):
            if (store.id,ingredient) not in existing_prices: session.add(StorePrice(store_id=store.id,ingredient_name=ingredient,price_per_unit=round(base*(1+index*.1),4),unit=unit))
    existing_recipes={recipe.title: recipe for recipe in (await session.scalars(select(Recipe))).all()}
    for title,ins,prep,cal,p,c,f,meal,tags,ingredients in RECIPES:
        if title in existing_recipes:
            # Upgrade the original compact seed catalog with current classification metadata.
            existing_recipes[title].meal_type, existing_recipes[title].tags = meal, tags
            continue
        recipe=Recipe(title=title,instructions=ins,prep_time=prep,calories=cal,protein_g=p,carbs_g=c,fat_g=f,meal_type=meal,tags=tags)
        session.add(recipe); await session.flush()
        session.add_all([RecipeIngredient(recipe_id=recipe.id,ingredient_name=n,required_qty=q,unit=u) for n,q,u in ingredients])
    await session.commit()
