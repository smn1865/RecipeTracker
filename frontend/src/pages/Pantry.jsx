import { useEffect, useState } from "react";

export function Pantry({ headers, apiUrl = "" }) {
  const [items, setItems] = useState([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [selected, setSelected] = useState(null);
  const [quantity, setQuantity] = useState(1);
  const [unit, setUnit] = useState("g");
  const [error, setError] = useState("");

  async function refresh() {
    const response = await fetch(`${apiUrl}/api/pantry`, { headers });
    if (response.ok) setItems(await response.json());
  }

  useEffect(() => {
    refresh();
    const listener = () => refresh();
    addEventListener("pantry:refresh", listener);
    return () => removeEventListener("pantry:refresh", listener);
  }, []);

  useEffect(() => {
    if (query.trim().length < 2 || selected?.name === query) {
      setResults([]);
      return;
    }
    const timer = setTimeout(() => {
      fetch(`${apiUrl}/api/search?q=${encodeURIComponent(query)}`, { headers })
        .then((response) => (response.ok ? response.json() : { ingredients: [] }))
        .then((data) => setResults(data.ingredients || []));
    }, 200);
    return () => clearTimeout(timer);
  }, [query, selected]);

  async function addItem(event) {
    event.preventDefault();
    if (!selected) {
      setError("Choose an ingredient from the search results.");
      return;
    }
    const response = await fetch(`${apiUrl}/api/pantry/items`, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({ ingredient_id: selected.id, quantity: +quantity, unit }),
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      setError(detail.detail || "Could not add this ingredient.");
      return;
    }
    setQuery("");
    setSelected(null);
    setResults([]);
    setError("");
    await refresh();
  }

  async function patchItem(id, changes) {
    const response = await fetch(`${apiUrl}/api/pantry/items/${id}`, {
      method: "PATCH",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify(changes),
    });
    if (response.ok) await refresh();
  }

  return (
    <section className="rounded-[2rem] bg-white p-5 shadow-sm sm:p-7">
      <header>
        <p className="text-sm font-bold text-sage">LIVE INVENTORY</p>
        <h2 className="text-3xl font-bold text-forest">Your pantry</h2>
        <p className="mt-1 text-sm text-ink/55">
          Recipe availability and sourcing costs update from these exact balances.
        </p>
      </header>

      <form onSubmit={addItem} className="relative mt-5 grid gap-3 md:grid-cols-[1fr_110px_100px_auto]">
        <div className="relative">
          <input
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setSelected(null);
            }}
            placeholder="Search ingredient…"
            className="w-full rounded-xl border border-forest/10 bg-cream px-4 py-3 outline-none focus:border-sage"
          />
          {results.length > 0 && (
            <div className="absolute z-20 mt-1 max-h-48 w-full overflow-auto rounded-xl border border-forest/10 bg-white p-1 shadow-xl">
              {results.map((ingredient) => (
                <button
                  type="button"
                  key={ingredient.id}
                  onClick={() => {
                    setSelected(ingredient);
                    setQuery(ingredient.name);
                    setResults([]);
                  }}
                  className="block w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-mint"
                >
                  {ingredient.name}
                </button>
              ))}
            </div>
          )}
        </div>
        <input
          aria-label="Quantity"
          type="number"
          min="0.001"
          step="any"
          value={quantity}
          onChange={(event) => setQuantity(event.target.value)}
          className="rounded-xl border border-forest/10 bg-cream px-3 py-3"
        />
        <select value={unit} onChange={(event) => setUnit(event.target.value)} className="rounded-xl border border-forest/10 bg-cream px-3 py-3">
          {["g", "kg", "oz", "lb", "ml", "L", "each"].map((value) => <option key={value}>{value}</option>)}
        </select>
        <button className="rounded-xl bg-forest px-5 py-3 font-bold text-white">Add stock</button>
      </form>
      {error && <p className="mt-2 text-sm font-semibold text-amber-700">{error}</p>}

      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((item) => (
          <article key={item.id} className="rounded-2xl bg-cream p-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <b className="capitalize text-forest">{item.ingredient_name}</b>
                <p className="text-xs text-ink/45">{item.expiration_date ? `Expires ${item.expiration_date}` : "No expiration date"}</p>
              </div>
              <button onClick={() => patchItem(item.id, { remove: true })} className="text-xs font-bold text-amber-700">Remove</button>
            </div>
            <div className="mt-3 flex gap-2">
              <input
                aria-label={`${item.ingredient_name} quantity`}
                type="number"
                min="0"
                step="any"
                defaultValue={item.quantity}
                onBlur={(event) => patchItem(item.id, { quantity: +event.target.value })}
                className="min-w-0 flex-1 rounded-lg border border-forest/10 bg-white px-3 py-2 font-bold"
              />
              <select
                value={item.unit}
                onChange={(event) => patchItem(item.id, { unit: event.target.value })}
                className="rounded-lg border border-forest/10 bg-white px-2"
              >
                {["g", "kg", "oz", "lb", "ml", "L", "each"].map((value) => <option key={value}>{value}</option>)}
              </select>
            </div>
          </article>
        ))}
        {!items.length && <p className="text-sm text-ink/50">Your pantry is empty. Add an ingredient to start matching recipes.</p>}
      </div>
    </section>
  );
}
