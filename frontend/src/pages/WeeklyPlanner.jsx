import { useEffect, useMemo, useState } from "react";
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
    [budget, setBudget] = useState(50),
    [result, setResult] = useState(null),
    [busy, setBusy] = useState(false);
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
    setBusy(true);
    const r = await fetch(`${apiUrl}/api/planner/auto-generate`, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({ weekly_budget: budget }),
    });
    if (r.ok) {
      const data = await r.json();
      setResult(data);
      setSelected(
        Object.fromEntries(
          data.meals.map((m) => [`${m.day}-${m.slot}`, m.recipe_id]),
        ),
      );
    }
    setBusy(false);
  }
  async function consolidate() {
    const assignments = Object.entries(selected)
      .filter(([, id]) => id)
      .map(([key, recipe_id]) => {
        const [day, slot] = key.split("-");
        return { day, slot, recipe_id };
      });
    const r = await fetch(`${apiUrl}/api/planner/consolidate`, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({ assignments, weekly_budget: budget }),
    });
    if (r.ok) {
      const data = await r.json();
      setResult({ ...data, total_cost_usd: data.total_cost });
      onShoppingList?.(data);
    }
  }
  const total = result?.total_cost_usd ?? result?.total_cost ?? 0,
    progress = Math.min(100, (total / budget) * 100);
  return (
    <section className="rounded-[2rem] bg-white p-5 shadow-sm sm:p-7">
      <header className="flex flex-col justify-between gap-5 lg:flex-row lg:items-center">
        <div>
          <p className="text-sm font-bold text-sage">7-DAY COST OPTIMIZER</p>
          <h2 className="text-3xl font-bold text-forest">Weekly meal plan</h2>
          <p className="mt-1 text-sm text-ink/55">
            Recipes with overlapping ingredients lower your basket cost.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <label className="rounded-xl bg-cream px-3 py-2 text-sm font-bold">
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
            className="rounded-xl bg-lime px-4 py-2 font-bold text-forest"
          >
            {busy ? "Optimizing…" : "Auto-Generate Money-Saving Diet"}
          </button>
        </div>
      </header>
      <div className="mt-6 grid gap-3 md:grid-cols-4">
        <div className="rounded-2xl bg-forest p-4 text-white">
          <span className="text-xs font-bold text-lime">TOTAL WEEKLY COST</span>
          <b className="mt-1 block text-3xl">{formatPrice(total)}</b>
          {result?.saved_via_overlap_usd != null && (
            <small className="text-lime">
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
          <div key={label} className="rounded-2xl bg-cream p-4">
            <span className="text-xs font-bold text-sage">{label}</span>
            <b className="mt-1 block text-xl">{value || "—"}</b>
          </div>
        ))}
      </div>
      <div className="mt-4">
        <div className="flex justify-between text-xs font-bold">
          <span>{formatPrice(total)} used</span>
          <span>{formatPrice(budget)} budget</span>
        </div>
        <div className="mt-2 h-3 overflow-hidden rounded-full bg-cream">
          <div
            className={
              result?.exceeds_budget ? "h-full bg-red-500" : "h-full bg-forest"
            }
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
      <div className="mt-7 grid gap-4 lg:grid-cols-7">
        {DAYS.map((day) => (
          <article
            key={day}
            className="rounded-2xl border border-forest/10 bg-cream/50 p-3"
          >
            <h3 className="mb-3 font-extrabold text-forest">{day}</h3>
            <div className="grid gap-3">
              {SLOTS.map((slot) => {
                const key = `${day}-${slot}`,
                  recipe = byId[selected[key]],
                  autoMeal = result?.meals?.find(
                    (m) => m.day === day && m.slot === slot,
                  ),
                  cost =
                    autoMeal?.estimated_cost_usd ??
                    recipe?.estimated_missing_cost ??
                    0;
                return (
                  <div
                    key={slot}
                    className="min-h-32 rounded-xl bg-white p-3 shadow-sm"
                  >
                    <span className="text-[10px] font-bold uppercase text-sage">
                      {slot}
                    </span>
                    {recipe ? (
                      <>
                        <b className="mt-1 block text-sm leading-tight">
                          {recipe.title}
                        </b>
                        <span className="mt-2 inline-block rounded-full bg-mint px-2 py-1 text-[10px] font-bold text-forest">
                          {formatPrice(cost)}
                        </span>
                        <div className="mt-2 flex gap-2 text-[10px] font-bold">
                          <button
                            onClick={() =>
                              setSelected({ ...selected, [key]: "" })
                            }
                            className="text-red-600"
                          >
                            Remove
                          </button>
                          <label className="cursor-pointer text-sage">
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
                        className="mt-2 w-full rounded-lg border border-forest/10 bg-white p-2 text-xs"
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
      <div className="mt-6 flex justify-end">
        <button
          onClick={consolidate}
          className="rounded-xl bg-forest px-5 py-3 font-bold text-white"
        >
          Generate Weekly Shopping List →
        </button>
      </div>
    </section>
  );
}
