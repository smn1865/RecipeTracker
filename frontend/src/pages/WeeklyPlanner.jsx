import { useEffect, useMemo, useState } from "react";
import { LocationBadge } from "../components/LocationBadge";
const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
  SLOTS = ["Breakfast", "Lunch", "Dinner"];
export function WeeklyPlanner({
  recipes,
  formatPrice,
  headers,
  apiUrl = "",
  onShoppingList,
}) {
  const [selected, setSelected] = useState({}),
    [plan, setPlan] = useState([]),
    [ingredients, setIngredients] = useState([]),
    [budget, setBudget] = useState(50),
    [result, setResult] = useState(null),
    [busy, setBusy] = useState(false),
    [consumeMeal, setConsumeMeal] = useState(null),
    [useDefault, setUseDefault] = useState(true),
    [usage, setUsage] = useState([]),
    [consumeError, setConsumeError] = useState(""),
    [generateError, setGenerateError] = useState("");
  useEffect(() => {
    const add = (e) =>
      setSelected((current) => ({
        ...current,
        [`${e.detail.day}-${e.detail.slot}`]: e.detail.recipeId,
      }));
    addEventListener("planner:add", add);
    return () => removeEventListener("planner:add", add);
  }, []);
  const byId = useMemo(
    () => Object.fromEntries(recipes.map((r) => [r.id, r])),
    [recipes],
  );
  async function autoGenerate() {
    setBusy(true); setGenerateError("");
    setSelected({});
    setPlan([]);
    setIngredients([]);
    setResult(null);
    onShoppingList?.({ meals: [], ingredients: [] });
    try {
      const response = await fetch(`${apiUrl}/api/planner/auto-generate`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ weekly_budget: budget }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not generate a weekly diet.");
      if (!Array.isArray(data.meals) || data.meals.length !== 21) throw new Error("The server returned an incomplete weekly plan.");
      const hydrated = Object.fromEntries(data.meals.map((meal) => [`${meal.day}-${meal.slot}`, meal.recipe_id]));
      setSelected(hydrated);
      setPlan(data.meals);
      setIngredients(Array.isArray(data.ingredients) ? data.ingredients : []);
      setResult(data);
      onShoppingList?.(data);
    } catch (error) {
      setGenerateError(error.message);
    } finally {
      setBusy(false);
    }
  }
  async function consolidate() {
    const assignments = Object.entries(selected)
      .filter(([, id]) => id)
      .map(([key, recipe_id]) => {
        const [day, slot] = key.split("-");
        return { day, slot, recipe_id };
      });
    setBusy(true); setGenerateError("");
    setPlan([]);
    setIngredients([]);
    setResult(null);
    onShoppingList?.({ meals: [], ingredients: [] });
    try {
      const response = await fetch(`${apiUrl}/api/planner/consolidate`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ assignments, weekly_budget: budget }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not generate the weekly shopping list.");
      setPlan(Array.isArray(data.meals) ? data.meals : []);
      setIngredients(Array.isArray(data.missing_ingredients) ? data.missing_ingredients : []);
      setResult({ ...data, total_cost_usd: data.total_cost });
      onShoppingList?.(data);
    } catch (error) {
      setGenerateError(error.message || "Could not generate the weekly shopping list.");
    } finally {
      setBusy(false);
    }
  }
  async function openConsumption(meal) {
    setConsumeError("");
    setUseDefault(true);
    const response = await fetch(`${apiUrl}/api/recipes/${meal.recipe_id}/sourcing`, { headers });
    const sourcing = response.ok ? await response.json() : { ingredients: [] };
    setUsage(
      (sourcing.ingredients || [])
        .filter((item) => item.ingredient_id)
        .map((item) => ({
          ingredient_id: item.ingredient_id,
          ingredient_name: item.ingredient_name,
          used_amount: item.required_quantity,
          unit: item.unit,
        })),
    );
    setConsumeMeal(meal);
  }
  async function confirmConsumption() {
    setBusy(true);
    const response = await fetch(`${apiUrl}/api/planner/meals/${consumeMeal.meal_id}/consume`, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({
        used_default_quantities: useDefault,
        custom_ingredient_usage: useDefault
          ? []
          : usage.map(({ ingredient_id, used_amount, unit }) => ({ ingredient_id, used_amount: +used_amount, unit })),
      }),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      setConsumeError(data.detail || "Could not update pantry stock.");
      setBusy(false);
      return;
    }
    const data = await response.json();
    setPlan((current) => current.map((meal) => meal.meal_id === data.meal_id ? { ...meal, eaten: true, eaten_at: data.eaten_at } : meal));
    setResult((current) => ({
      ...current,
      meals: (current?.meals || []).map((meal) => meal.meal_id === data.meal_id ? { ...meal, eaten: true, eaten_at: data.eaten_at } : meal),
    }));
    dispatchEvent(new CustomEvent("pantry:refresh"));
    setConsumeMeal(null);
    setBusy(false);
  }
  const total = result?.total_cost_usd ?? result?.total_cost ?? 0,
    progress = Math.min(100, (total / budget) * 100);
  return (
    <section className="rounded-2xl border border-slate-800/10 bg-white p-5 shadow-sm sm:p-7">
      <header className="flex flex-col justify-between gap-5 lg:flex-row lg:items-center">
        <div>
          <p className="text-sm font-bold text-emerald-700">7-DAY COST OPTIMIZER</p>
          <div className="flex flex-wrap items-center gap-3"><h2 className="text-3xl font-bold text-zinc-900">Weekly meal plan</h2><LocationBadge/></div>
          <p className="mt-1 text-sm text-slate-800/70">
            Recipes with overlapping ingredients lower your basket cost.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <label className="rounded-xl bg-amber-500 px-3 py-2 text-sm font-bold text-zinc-900">
            Budget $
            <input
              className="ml-2 w-16 bg-transparent outline-none"
              type="number"
              min="1"
              value={budget}
              onChange={(e) => setBudget(+e.target.value)}
            />
          </label>
          <button
            onClick={autoGenerate}
            disabled={busy}
            className="rounded-xl bg-emerald-700 px-4 py-2 font-bold text-white disabled:opacity-50"
          >
            {busy ? "Optimizing…" : "Auto-Generate Money-Saving Diet"}
          </button>
        </div>
      </header>
      {generateError && <p role="alert" className="mt-4 rounded-xl border border-slate-800/10 bg-slate-100 p-3 text-sm font-semibold text-slate-800">{generateError}</p>}
      <div className="mt-6 grid gap-3 md:grid-cols-4">
        <div className="rounded-2xl bg-zinc-900 p-4 text-white">
          <span className="text-xs font-bold text-slate-100">TOTAL WEEKLY COST</span>
          <b className="mt-1 block text-3xl text-amber-500">{formatPrice(total)}</b>
          {result?.saved_via_overlap_usd != null && (
            <small className="text-amber-500">
              Saved {formatPrice(result.saved_via_overlap_usd)} via overlap
            </small>
          )}
        </div>
        {[
          ["Calories", result?.total_calories],
          ["Protein", result?.total_protein_g && `${result.total_protein_g}g`],
          [
            "Carbs / Fats",
            result?.total_carbs_g &&
              `${result.total_carbs_g}g / ${result.total_fat_g}g`,
          ],
        ].map(([label, value]) => (
          <div key={label} className="rounded-2xl border border-slate-800/10 bg-slate-100 p-4">
            <span className="text-xs font-bold text-slate-800/70">{label}</span>
            <b className="mt-1 block text-xl">{value || "—"}</b>
          </div>
        ))}
      </div>
      <div className="mt-4">
        <div className="flex justify-between text-xs font-bold">
          <span>{formatPrice(total)} used</span>
          <span>{formatPrice(budget)} budget</span>
        </div>
        <div className="mt-2 h-3 overflow-hidden rounded-full bg-slate-100">
          <div
            className={
              result?.exceeds_budget ? "h-full bg-amber-500" : "h-full bg-emerald-700"
            }
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
      <div className="mt-7 grid gap-4 lg:grid-cols-7">
        {DAYS.map((day) => (
          <article
            key={day}
            className="rounded-2xl border border-slate-800/10 bg-slate-100 p-3"
          >
            <h3 className="mb-3 font-extrabold text-zinc-900">{day}</h3>
            <div className="grid gap-3">
              {SLOTS.map((slot) => {
                const key = `${day}-${slot}`,
                  autoMeal = plan.find(
                    (m) => m.day === day && m.slot === slot,
                  ),
                  selection = selected[key],
                  recipe = selection === "" ? null : byId[selection] || autoMeal,
                  isPersistedAutoMeal = Number(selection) === autoMeal?.recipe_id,
                  cost =
                    (byId[selection]?.estimated_missing_cost ??
                    autoMeal?.estimated_cost_usd ??
                    recipe?.estimated_missing_cost) ??
                    0;
                return (
                  <div
                    key={slot}
                    className={`min-h-32 rounded-xl border p-3 ${autoMeal?.eaten ? "border-emerald-600 bg-white" : "border-slate-800/10 bg-white"}`}
                  >
                    <span className="text-[10px] font-bold uppercase text-slate-800/70">
                      {slot}
                    </span>
                    {recipe ? (
                      <>
                        <b className="mt-1 block text-sm leading-tight">
                          {recipe.title}
                        </b>
                        <span className="mt-2 inline-block rounded-full bg-amber-500 px-2 py-1 text-[10px] font-bold text-zinc-900">
                          {formatPrice(cost)}
                        </span>
                        <div className="mt-2 flex gap-2 text-[10px] font-bold">
                          {autoMeal?.eaten ? (
                            <span className="text-emerald-700">✓ Eaten</span>
                          ) : autoMeal?.meal_id && isPersistedAutoMeal ? (
                            <button onClick={() => openConsumption(autoMeal)} className="rounded-full bg-emerald-700 px-2 py-1 text-white">
                              Mark as Eaten
                            </button>
                          ) : null}
                          <button
                            onClick={() =>
                              setSelected({ ...selected, [key]: "" })
                            }
                            className="text-slate-800/70"
                          >
                            Remove
                          </button>
                          <label className="cursor-pointer text-slate-800/70">
                            Replace
                            <select
                              className="sr-only"
                              value={selected[key]}
                              onChange={(e) =>
                                setSelected({
                                  ...selected,
                                  [key]: +e.target.value,
                                })
                              }
                            >
                              {recipes.map((r) => (
                                <option key={r.id} value={r.id}>
                                  {r.title}
                                </option>
                              ))}
                            </select>
                          </label>
                        </div>
                      </>
                    ) : (
                      <select
                        aria-label={`${day} ${slot}`}
                        className="mt-2 w-full rounded-lg border border-slate-800/10 bg-white p-2 text-xs"
                        value=""
                        onChange={(e) =>
                          setSelected({ ...selected, [key]: +e.target.value })
                        }
                      >
                        <option value="">Add meal</option>
                        {recipes
                          .filter((r) => r.meal_type === slot)
                          .map((r) => (
                            <option key={r.id} value={r.id}>
                              {r.title}
                            </option>
                          ))}
                      </select>
                    )}
                  </div>
                );
              })}
            </div>
          </article>
        ))}
      </div>
      {result && <section className="mt-6 rounded-2xl border border-slate-200 bg-emerald-50 p-5"><div className="flex items-center justify-between"><div><p className="text-xs font-bold text-emerald-700">HYDRATED SHOPPING LIST</p><h3 className="text-xl font-bold text-slate-900">Weekly ingredients</h3></div><span className="rounded-full bg-teal-100 px-3 py-1 text-xs font-bold text-teal-800">{ingredients.length} items</span></div><div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{ingredients.map((item)=><div key={`${item.ingredient_name}-${item.unit}`} className="flex justify-between rounded-xl border border-emerald-200 bg-white p-3 text-sm"><span className="capitalize font-bold text-slate-900">{item.ingredient_name}<small className="block font-normal text-slate-600">{item.quantity}{item.unit}</small></span>{item.estimated_cost_usd!=null&&<b className="text-amber-700">{formatPrice(item.estimated_cost_usd)}</b>}</div>)}</div></section>}
      <div className="mt-6 flex justify-end">
        <button
          onClick={consolidate}
          disabled={busy}
          className="rounded-xl bg-emerald-700 px-5 py-3 font-bold text-white disabled:cursor-wait disabled:opacity-50"
        >
          Generate Weekly Shopping List →
        </button>
      </div>
      {consumeMeal && (
        <div className="fixed inset-0 z-50 overflow-auto bg-emerald-700/50 p-4 backdrop-blur-sm">
          <section className="mx-auto my-16 max-w-xl rounded-[2rem] bg-white p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold text-emerald-600">UPDATE PANTRY AFTER MEAL</p>
                <h3 className="mt-1 text-2xl font-bold text-emerald-700">Did you use standard recipe portions?</h3>
                <p className="mt-1 text-sm text-zinc-900/55">{consumeMeal.title}</p>
              </div>
              <button onClick={() => setConsumeMeal(null)} className="text-2xl">×</button>
            </div>
            <div className="mt-5 grid grid-cols-2 rounded-xl bg-slate-100 p-1 text-sm font-bold">
              <button onClick={() => setUseDefault(true)} className={useDefault ? "rounded-lg bg-emerald-700 px-3 py-3 text-white" : "px-3 py-3"}>Yes, use defaults</button>
              <button onClick={() => setUseDefault(false)} className={!useDefault ? "rounded-lg bg-emerald-700 px-3 py-3 text-white" : "px-3 py-3"}>No, adjust amounts</button>
            </div>
            {!useDefault && (
              <div className="mt-5 max-h-72 space-y-2 overflow-auto">
                {usage.map((item, index) => (
                  <label key={item.ingredient_id} className="grid grid-cols-[1fr_100px_60px] items-center gap-2 rounded-xl bg-slate-100 p-3 text-sm">
                    <span className="capitalize font-bold">{item.ingredient_name}</span>
                    <input
                      type="number"
                      min="0.001"
                      step="any"
                      value={item.used_amount}
                      onChange={(event) => setUsage((current) => current.map((entry, i) => i === index ? { ...entry, used_amount: event.target.value } : entry))}
                      className="min-w-0 rounded-lg border border-emerald-700/10 bg-white px-2 py-2"
                    />
                    <span>{item.unit}</span>
                  </label>
                ))}
                {!usage.length && <p className="text-sm text-slate-800">No canonical ingredients are available for custom deduction.</p>}
              </div>
            )}
            {consumeError && <p className="mt-3 text-sm font-semibold text-slate-800">{consumeError}</p>}
            <div className="mt-6 flex justify-end gap-2">
              <button onClick={() => setConsumeMeal(null)} className="rounded-xl bg-slate-100 px-4 py-3 font-bold">Cancel</button>
              <button disabled={busy || (!useDefault && !usage.length)} onClick={confirmConsumption} className="rounded-xl bg-emerald-700 px-5 py-3 font-bold text-white disabled:opacity-40">
                {busy ? "Updating…" : "Confirm & deduct stock"}
              </button>
            </div>
          </section>
        </div>
      )}
    </section>
  );
}
