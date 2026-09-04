import { useEffect, useState } from "react";
import { IngredientDetailModal } from "./IngredientDetailModal";
const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
  SLOTS = ["Breakfast", "Lunch", "Dinner"];
export function GlobalSearch({ headers, apiUrl = "", formatPrice }) {
  const [q, setQ] = useState(""),
    [results, setResults] = useState(null),
    [ingredient, setIngredient] = useState(null),
    [dish, setDish] = useState(null),
    [day, setDay] = useState("Mon"),
    [slot, setSlot] = useState("Breakfast");
  useEffect(() => {
    if (q.trim().length < 2) {
      setResults(null);
      return;
    }
    const timer = setTimeout(
      () =>
        fetch(`${apiUrl}/api/search?q=${encodeURIComponent(q)}`, { headers })
          .then((r) => r.json())
          .then(setResults),
      250,
    );
    return () => clearTimeout(timer);
  }, [q]);
  function add() {
    dispatchEvent(
      new CustomEvent("planner:add", {
        detail: { day, slot, recipeId: dish.id },
      }),
    );
    setDish(null);
    setQ("");
    setResults(null);
  }
  return (
    <div className="relative z-30 w-full max-w-xl">
      <label className="sr-only" htmlFor="global-search">
        Search dishes and ingredients
      </label>
      <input
        id="global-search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search dishes or ingredients…"
        className="w-full rounded-2xl border border-forest/10 bg-white px-5 py-3 shadow-sm outline-none focus:ring-4 focus:ring-mint"
      />
      {results && (
        <div className="absolute mt-2 max-h-[70vh] w-full overflow-auto rounded-2xl bg-white p-3 shadow-2xl">
          <p className="px-2 py-1 text-xs font-bold text-sage">DISHES</p>
          {results.dishes.map((item) => (
            <button
              key={`d-${item.id}`}
              onClick={() => setDish(item)}
              className="flex w-full justify-between rounded-xl p-3 text-left hover:bg-cream"
            >
              <span>
                <b>{item.title}</b>
                <small className="block text-ink/50">
                  {item.meal_type} · {item.calories} kcal
                </small>
              </span>
              <b>{formatPrice(item.estimated_cost_usd)}</b>
            </button>
          ))}
          <p className="mt-2 px-2 py-1 text-xs font-bold text-sage">
            INGREDIENTS
          </p>
          {results.ingredients.map((item) => (
            <button
              key={`i-${item.id}`}
              onClick={() => setIngredient(item.id)}
              className="flex w-full justify-between rounded-xl p-3 text-left hover:bg-cream"
            >
              <b className="capitalize">{item.name}</b>
              <b>
                {formatPrice(item.estimated_cost_usd)} / {item.unit}
              </b>
            </button>
          ))}
        </div>
      )}
      {dish && (
        <div className="fixed inset-0 z-40 grid place-items-center bg-forest/45 p-4">
          <div className="w-full max-w-md rounded-3xl bg-white p-6">
            <h2 className="text-2xl font-bold">{dish.title}</h2>
            <p className="mt-2 text-ink/60">
              {dish.calories} kcal · {formatPrice(dish.estimated_cost_usd)}
            </p>
            <div className="mt-5 grid grid-cols-2 gap-2">
              <select
                value={day}
                onChange={(e) => setDay(e.target.value)}
                className="rounded-xl border p-3"
              >
                {DAYS.map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
              <select
                value={slot}
                onChange={(e) => setSlot(e.target.value)}
                className="rounded-xl border p-3"
              >
                {SLOTS.map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button
                onClick={() => setDish(null)}
                className="px-4 py-2 font-bold"
              >
                Cancel
              </button>
              <button
                onClick={add}
                className="rounded-xl bg-forest px-4 py-2 font-bold text-white"
              >
                Add to Weekly Planner
              </button>
            </div>
          </div>
        </div>
      )}
      {ingredient && (
        <IngredientDetailModal
          ingredientId={ingredient}
          headers={headers}
          apiUrl={apiUrl}
          formatPrice={formatPrice}
          onClose={() => setIngredient(null)}
        />
      )}
    </div>
  );
}
