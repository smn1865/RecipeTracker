from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Ingredient, LocalStore, Recipe, RecipeIngredient, StoreInventoryItem, StorePrice
from ..seed import RECIPES as CORE_RECIPES, seed as seed_core

# title, instructions, minutes, kcal, protein, carbs, fat, meal type, tags, exact requirements
EXTRA_RECIPES = [
    ("Spas Yogurt Soup", "1. Simmer wheat berries until tender. 2. Whisk yogurt with egg and temper with broth. 3. Add wheat, finish with mint, and serve warm.", 35, 360, 20, 48, 10, "Lunch", "Armenian,Vegetarian,Budget Friendly", [("wheat berries",80,"g"),("matzoon",250,"g"),("egg",1,"each"),("mint",8,"g")]),
    ("Ghapama Stuffed Pumpkin", "1. Roast the pumpkin shell until just tender. 2. Fold rice with dried fruit, walnuts, honey, and cinnamon. 3. Fill the pumpkin and bake until fragrant.", 75, 520, 11, 91, 15, "Dinner", "Armenian,Vegetarian", [("pumpkin",350,"g"),("brown rice",90,"g"),("dried apricot",35,"g"),("walnut",25,"g"),("honey",15,"g")]),
    ("Lean Khorovats Plate", "1. Marinate pork with onion and paprika. 2. Grill with peppers until browned and cooked through. 3. Rest, slice, and serve with tomato salad.", 45, 610, 48, 28, 31, "Dinner", "Armenian,High Protein", [("pork loin",190,"g"),("onion",80,"g"),("bell pepper",120,"g"),("tomato",120,"g")]),
    ("Chicken Khorovats Bowl", "1. Season chicken and thread with vegetables. 2. Grill until the chicken reaches a safe temperature. 3. Serve over bulgur with herbs.", 35, 560, 50, 58, 14, "Dinner", "Armenian,High Protein", [("chicken breast",190,"g"),("bulgur",90,"g"),("bell pepper",100,"g"),("parsley",15,"g")]),
    ("Harissa Chicken Porridge", "1. Soak cracked wheat. 2. Simmer wheat and chicken slowly until creamy. 3. Shred the chicken, stir vigorously, and season.", 80, 590, 46, 70, 13, "Dinner", "Armenian,High Protein,Budget Friendly", [("cracked wheat",110,"g"),("chicken breast",170,"g"),("butter",10,"g")]),
    ("Baked Ishkhan with Herbs", "1. Season trout with lemon and herbs. 2. Bake until the flesh flakes easily. 3. Serve with roasted potatoes and greens.", 32, 570, 44, 45, 23, "Dinner", "Armenian,High Protein", [("trout",190,"g"),("potato",220,"g"),("lemon",40,"g"),("parsley",12,"g")]),
    ("Eech Bulgur Salad", "1. Bloom bulgur in hot tomato broth. 2. Fold in herbs, scallion, and lemon. 3. Rest ten minutes and serve with lettuce.", 25, 420, 13, 75, 8, "Lunch", "Armenian,Vegetarian,Budget Friendly", [("bulgur",100,"g"),("tomato",160,"g"),("parsley",20,"g"),("scallion",25,"g"),("lemon",30,"g")]),
    ("Pasuts Tolma", "1. Soak and cook beans and lentils. 2. Season the filling and wrap in cabbage leaves. 3. Simmer the rolls in tomato broth until tender.", 65, 490, 23, 82, 8, "Dinner", "Armenian,Vegan,Budget Friendly", [("lentils",70,"g"),("chickpeas",70,"g"),("black beans",70,"g"),("cabbage",180,"g"),("tomato",120,"g")]),
    ("Lahmajoun Protein Plate", "1. Mix lean beef with tomato, pepper, and herbs. 2. Spread thinly over flatbread. 3. Bake hot and serve with lemon salad.", 30, 540, 38, 57, 18, "Lunch", "Armenian,High Protein", [("lean beef",140,"g"),("bread",100,"g"),("tomato",100,"g"),("bell pepper",60,"g"),("parsley",10,"g")]),
    ("Jingalov Hats Herb Flatbread", "1. Chop mixed herbs and season lightly. 2. Enclose the herbs in thin dough. 3. Griddle both sides until spotted and crisp.", 28, 390, 14, 68, 8, "Lunch", "Armenian,Vegetarian,Budget Friendly", [("bread",120,"g"),("spinach",80,"g"),("parsley",25,"g"),("scallion",35,"g")]),
    ("Armenian Lentil Kofte", "1. Cook lentils until soft. 2. Mix with bulgur, sautéed onion, and herbs. 3. Shape into kofte and chill before serving.", 40, 430, 21, 73, 8, "Lunch", "Armenian,Vegan,Budget Friendly", [("lentils",120,"g"),("bulgur",70,"g"),("onion",70,"g"),("parsley",15,"g")]),
    ("Matzoon Cucumber Bowl", "1. Grate cucumber and drain. 2. Stir into matzoon with mint. 3. Top with walnuts and serve chilled.", 8, 270, 17, 18, 15, "Snack", "Armenian,Quick & Easy", [("matzoon",220,"g"),("cucumber",140,"g"),("mint",6,"g"),("walnut",18,"g")]),
    ("Apricot Walnut Oats", "1. Simmer oats with milk. 2. Fold in chopped apricots and cinnamon. 3. Top with walnuts and yogurt.", 10, 440, 20, 62, 15, "Breakfast", "Armenian,Vegetarian", [("oats",70,"g"),("milk",220,"ml"),("apricot",100,"g"),("walnut",18,"g"),("greek yogurt",80,"g")]),
    ("Lavash Egg Breakfast Wrap", "1. Scramble eggs with spinach. 2. Warm lavash and add the filling. 3. Roll tightly with tomato and yogurt sauce.", 12, 410, 27, 39, 17, "Breakfast", "Armenian,High Protein,Quick & Easy", [("egg",3,"each"),("bread",75,"g"),("spinach",60,"g"),("tomato",80,"g")]),
    ("Buckwheat Matzoon Bowl", "1. Simmer buckwheat until fluffy. 2. Spoon over matzoon. 3. Finish with cucumber, herbs, and toasted seeds.", 18, 400, 22, 55, 11, "Breakfast", "Vegetarian,Budget Friendly", [("buckwheat",90,"g"),("matzoon",180,"g"),("cucumber",80,"g"),("sunflower seeds",15,"g")]),
    ("Herbed Chickpea Lavash", "1. Mash chickpeas with yogurt and lemon. 2. Add herbs and cucumber. 3. Wrap in lavash and toast briefly.", 12, 450, 20, 66, 12, "Lunch", "Vegetarian,Budget Friendly", [("chickpeas",160,"g"),("bread",80,"g"),("greek yogurt",50,"g"),("cucumber",90,"g"),("parsley",12,"g")]),
    ("Pomegranate Chicken Salad", "1. Sear seasoned chicken and rest. 2. Toss greens, pomegranate, and walnuts. 3. Slice chicken over the salad and dress with lemon.", 22, 480, 43, 28, 22, "Lunch", "Armenian,High Protein", [("chicken breast",170,"g"),("spinach",100,"g"),("pomegranate",90,"g"),("walnut",18,"g"),("lemon",25,"g")]),
    ("Mushroom Bulgur Pilaf", "1. Brown mushrooms and onion. 2. Toast bulgur in the pan. 3. Add broth and simmer covered until fluffy.", 28, 430, 16, 72, 9, "Dinner", "Vegetarian,Budget Friendly", [("bulgur",110,"g"),("mushroom",160,"g"),("onion",70,"g"),("butter",8,"g")]),
    ("Chicken Quinoa Power Bowl", "1. Cook quinoa. 2. Sear chicken and roast broccoli. 3. Assemble with lemon yogurt dressing.", 28, 610, 52, 64, 17, "Lunch", "High Protein,Meal Prep", [("chicken breast",180,"g"),("quinoa",95,"g"),("broccoli",130,"g"),("greek yogurt",50,"g")]),
    ("Turkey Spinach Protein Pasta", "1. Boil pasta until al dente. 2. Brown turkey with garlic and tomato. 3. Fold in spinach and pasta.", 25, 590, 47, 68, 14, "Dinner", "High Protein,Meal Prep", [("turkey",160,"g"),("pasta",110,"g"),("spinach",80,"g"),("tomato",140,"g")]),
    ("Tuna White Bean Salad", "1. Rinse beans and drain tuna. 2. Toss with tomato, cucumber, and herbs. 3. Dress with lemon and chill.", 10, 440, 39, 46, 11, "Lunch", "High Protein,Quick & Easy", [("tuna",120,"g"),("white beans",150,"g"),("tomato",100,"g"),("cucumber",100,"g")]),
    ("Beef Broccoli Stir-Fry", "1. Sear thin beef strips. 2. Stir-fry broccoli and pepper. 3. Return beef, add sauce, and serve over rice.", 24, 630, 45, 67, 20, "Dinner", "High Protein", [("lean beef",170,"g"),("broccoli",150,"g"),("brown rice",95,"g"),("bell pepper",80,"g")]),
    ("Ginger Tofu Noodle Bowl", "1. Crisp tofu in a hot pan. 2. Cook noodles and vegetables. 3. Toss together with ginger sauce.", 22, 520, 27, 68, 17, "Dinner", "Vegan,Quick & Easy", [("tofu",190,"g"),("noodles",100,"g"),("broccoli",100,"g"),("carrot",80,"g")]),
    ("Red Lentil Coconut Curry", "1. Sauté onion and spices. 2. Simmer lentils with tomato and coconut milk. 3. Fold in spinach and serve.", 30, 510, 22, 69, 17, "Dinner", "Vegan,Budget Friendly", [("lentils",140,"g"),("coconut milk",120,"ml"),("tomato",140,"g"),("spinach",80,"g")]),
    ("Black Bean Corn Bowl", "1. Cook rice. 2. Warm beans and corn with spices. 3. Add tomato salsa and yogurt.", 18, 540, 23, 91, 10, "Lunch", "Vegetarian,Budget Friendly", [("black beans",160,"g"),("brown rice",90,"g"),("corn",100,"g"),("tomato",100,"g"),("greek yogurt",40,"g")]),
    ("Sardine Potato Salad", "1. Boil potatoes until tender. 2. Flake sardines and chop cucumber. 3. Toss with yogurt mustard dressing.", 22, 470, 32, 46, 18, "Lunch", "High Protein,Budget Friendly", [("sardines",120,"g"),("potato",220,"g"),("cucumber",90,"g"),("greek yogurt",50,"g")]),
    ("Egg Fried Brown Rice", "1. Scramble eggs and set aside. 2. Stir-fry rice with peas and carrot. 3. Return eggs and season.", 16, 500, 24, 67, 16, "Dinner", "Quick & Easy,Budget Friendly", [("egg",3,"each"),("brown rice",110,"g"),("peas",90,"g"),("carrot",70,"g")]),
    ("Cottage Cheese Berry Bowl", "1. Spoon cottage cheese into a bowl. 2. Add berries and sliced banana. 3. Sprinkle with seeds.", 5, 330, 29, 37, 9, "Breakfast", "High Protein,Quick & Easy", [("cottage cheese",220,"g"),("berries",100,"g"),("banana",70,"g"),("sunflower seeds",12,"g")]),
    ("Savory Lentil Breakfast", "1. Warm cooked lentils with tomato. 2. Fry an egg to preference. 3. Layer with spinach and herbs.", 14, 390, 25, 45, 13, "Breakfast", "High Protein,Budget Friendly", [("lentils",130,"g"),("egg",2,"each"),("tomato",100,"g"),("spinach",60,"g")]),
    ("Apple Cinnamon Quinoa", "1. Simmer quinoa in milk. 2. Add diced apple and cinnamon. 3. Finish with yogurt and walnuts.", 20, 430, 18, 65, 12, "Breakfast", "Vegetarian", [("quinoa",80,"g"),("milk",200,"ml"),("apple",130,"g"),("greek yogurt",80,"g"),("walnut",12,"g")]),
    ("Hummus Vegetable Snack Box", "1. Slice cucumber, carrot, and pepper. 2. Portion hummus. 3. Pack with toasted bread wedges.", 8, 350, 13, 48, 13, "Snack", "Vegan,Meal Prep", [("hummus",90,"g"),("cucumber",100,"g"),("carrot",90,"g"),("bell pepper",80,"g"),("bread",50,"g")]),
    ("Roasted Chickpea Crunch", "1. Dry chickpeas thoroughly. 2. Toss with paprika and a little oil. 3. Roast until crisp, shaking once.", 32, 280, 14, 42, 7, "Snack", "Vegan,Budget Friendly", [("chickpeas",170,"g"),("paprika",3,"g")]),
    ("Yogurt Apricot Protein Cup", "1. Chop apricots. 2. Layer with yogurt and cottage cheese. 3. Top with seeds.", 5, 300, 28, 32, 7, "Snack", "Armenian,High Protein", [("greek yogurt",160,"g"),("cottage cheese",100,"g"),("apricot",100,"g"),("sunflower seeds",10,"g")]),
    ("Peanut Oat Energy Bites", "1. Mix oats, peanut butter, and honey. 2. Fold in chopped dried fruit. 3. Roll and chill until firm.", 12, 310, 11, 39, 14, "Snack", "Meal Prep,Budget Friendly", [("oats",55,"g"),("peanut butter",35,"g"),("honey",15,"g"),("dried apricot",20,"g")]),
    ("Lemon Salmon Quinoa", "1. Bake salmon with lemon. 2. Simmer quinoa and steam spinach. 3. Plate together with herb yogurt.", 30, 620, 45, 55, 25, "Dinner", "High Protein", [("salmon",170,"g"),("quinoa",90,"g"),("spinach",90,"g"),("lemon",35,"g")]),
    ("Budget Chicken Lentil Stew", "1. Brown chicken pieces. 2. Add lentils, tomato, carrot, and broth. 3. Simmer until thick and tender.", 38, 540, 48, 58, 13, "Dinner", "High Protein,Budget Friendly", [("chicken breast",150,"g"),("lentils",100,"g"),("tomato",130,"g"),("carrot",90,"g")]),
]

BASE_PRICE = {"egg":.10,"chicken breast":.009,"salmon":.018,"trout":.016,"lean beef":.013,"pork loin":.010,"turkey":.011,"tuna":.012,"sardines":.009,"matzoon":.0045,"greek yogurt":.006,"milk":.0018,"cottage cheese":.0065,"butter":.012,"walnut":.018,"honey":.012,"lemon":.004,"mint":.016,"parsley":.010,"paprika":.020}
STORE_DATA = [("Yerevan City",40.1792,44.4991,"12 Abovyan St"),("SAS",40.1850,44.5100,"5 Tumanyan St"),("Carrefour",40.1720,44.4920,"21 Mashtots Ave"),("Parma",40.1908,44.5156,"Komitas Ave"),("Evrika",40.1818,44.5231,"Khanjyan St")]

async def seed(session: AsyncSession):
    await seed_core(session)
    stores=(await session.scalars(select(LocalStore).order_by(LocalStore.id))).all()
    for index,data in enumerate(STORE_DATA):
        if index < len(stores):
            stores[index].name,stores[index].lat,stores[index].lon,stores[index].address=data
        else:
            store=LocalStore(name=data[0],lat=data[1],lon=data[2],address=data[3]);session.add(store);stores.append(store)
    await session.flush()
    existing={item.title for item in (await session.scalars(select(Recipe))).all()}
    for title,instructions,prep,calories,protein,carbs,fat,meal,tags,ingredients in EXTRA_RECIPES:
        if title in existing: continue
        recipe=Recipe(title=title,instructions=instructions,prep_time=prep,calories=calories,protein_g=protein,carbs_g=carbs,fat_g=fat,meal_type=meal,tags=tags)
        session.add(recipe);await session.flush()
        session.add_all([RecipeIngredient(recipe_id=recipe.id,ingredient_name=name,required_qty=quantity,unit=unit) for name,quantity,unit in ingredients])
    all_recipes=CORE_RECIPES+EXTRA_RECIPES
    names={name for recipe in all_recipes for name,_,_ in recipe[-1]}
    existing_ingredients={item.name for item in (await session.scalars(select(Ingredient))).all()}
    for name in names-existing_ingredients:
        session.add(Ingredient(name=name,calories_per_100g=100,protein_g_per_100g=5,fat_g_per_100g=2,carbs_g_per_100g=16,fiber_g_per_100g=2.5))
    await session.flush()
    prices={(item.store_id,item.ingredient_name,item.unit):item for item in (await session.scalars(select(StorePrice))).all()}
    inventory={(item.store_id,item.ingredient_name,item.unit):item for item in (await session.scalars(select(StoreInventoryItem))).all()}
    count_names={name for recipe in all_recipes for name,_,unit in recipe[-1] if unit=="each"}
    volume_names={name for recipe in all_recipes for name,_,unit in recipe[-1] if unit=="ml"}
    for name in names:
        unit="each" if name in count_names else "ml" if name in volume_names else "g"
        base=BASE_PRICE.get(name,.0035 if unit!="each" else .25)
        package_size=12 if unit=="each" else 1000 if unit=="ml" else 500
        rotation=sum(ord(char) for char in name)%len(stores)
        for index,store in enumerate(stores):
            factor=[.86,.94,1.0,1.07,1.14][(index-rotation)%5]
            unit_price=round(base*factor,4)
            price_key=(store.id,name,unit)
            if price_key in prices: prices[price_key].price_per_unit=unit_price
            else: session.add(StorePrice(store_id=store.id,ingredient_name=name,price_per_unit=unit_price,unit=unit))
            inventory_key=(store.id,name,unit)
            package_price=round(unit_price*package_size,2)
            if inventory_key in inventory:
                inventory[inventory_key].package_size=package_size;inventory[inventory_key].price_usd=package_price
            else: session.add(StoreInventoryItem(store_id=store.id,ingredient_name=name,package_size=package_size,unit=unit,price_usd=package_price,in_stock=True))
    await session.commit()
