import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { SourcingPanel } from "./components/SourcingPanel";
import { WeeklyPlanner } from "./pages/WeeklyPlanner";
import { GlobalSearch } from "./components/GlobalSearch";
import { RecipeCard } from "./components/RecipeCard";
import { Pantry } from "./pages/Pantry";
import "./styles.css";
const API = import.meta.env.VITE_API_URL || "http://localhost:8000",
  FALLBACK = { lat: 40.1872, lon: 44.5152 };
// Kept true only to retain the compact form's optional manual-coordinate branch; no Maps key or SDK is used.
const mapsKey = true;
const go = (p) => {
  history.pushState({}, "", p);
  dispatchEvent(new PopStateEvent("popstate"));
};
const CurrencyContext = createContext(null);
function formatPrice(usdAmount, currencyMode = "USD", localSymbol = "$", usdToLocalRate = 1) {
  const amount = Number(usdAmount || 0);
  return currencyMode === "LOCAL"
    ? `${(amount * usdToLocalRate).toLocaleString(undefined, { maximumFractionDigits: 2 })} ${localSymbol}`
    : `$${amount.toFixed(2)}`;
}
function CurrencyProvider({ children }) {
  const [currencyMode, setCurrencyMode] = useState("LOCAL");
  const [currency, setCurrency] = useState({ localCurrency: "AMD", localSymbol: "֏", usdToLocalRate: 388 });
  const configureCurrency = (data) => setCurrency({ localCurrency: data.local_currency || "AMD", localSymbol: data.local_currency_symbol || "֏", usdToLocalRate: Number(data.usd_to_local_rate || 388) });
  return <CurrencyContext.Provider value={{ currencyMode, setCurrencyMode, ...currency, configureCurrency, formatPrice: (amount) => formatPrice(amount, currencyMode, currency.localSymbol, currency.usdToLocalRate) }}>{children}</CurrencyContext.Provider>;
}
const useCurrency = () => useContext(CurrencyContext);
function CurrencySwitcher() {
  const { currencyMode, setCurrencyMode, localCurrency, localSymbol } = useCurrency();
  return <div className="inline-flex rounded-full bg-white/10 p-1 text-xs font-bold"><button onClick={() => setCurrencyMode("LOCAL")} className={currencyMode === "LOCAL" ? "rounded-full bg-lime px-3 py-1.5 text-forest" : "px-3 py-1.5 text-ink/60"}>{localCurrency} {localSymbol}</button><button onClick={() => setCurrencyMode("USD")} className={currencyMode === "USD" ? "rounded-full bg-lime px-3 py-1.5 text-forest" : "px-3 py-1.5 text-ink/60"}>USD $</button></div>;
}
const Btn = ({ children, onClick, type = "button", plain = false }) => (
  <button
    type={type}
    onClick={onClick}
    className={
      plain
        ? "rounded-xl px-5 py-3 font-bold text-forest hover:bg-cream"
        : "rounded-xl bg-forest px-5 py-3 font-bold text-white shadow-lg shadow-forest/15 transition hover:-translate-y-0.5"
    }
  >
    {children}
  </button>
);
const Logo = () => (
  <button
    onClick={() => go("/")}
    className="flex items-center gap-2 text-xl font-extrabold text-forest"
  >
    <span className="grid h-8 w-8 place-items-center rounded-lg bg-lime">
      ✦
    </span>
    pantr<span className="text-sage">wise</span>
  </button>
);
const Field = ({ label, value, set, type = "text", error }) => (
  <label className="mb-4 block text-sm font-bold">
    {label}
    <input
      type={type}
      required
      value={value}
      onChange={(e) => set(e.target.value)}
      className={`mt-1 w-full rounded-xl border bg-white px-4 py-3 outline-none focus:border-sage focus:ring-4 focus:ring-mint ${error ? "border-red-400" : "border-forest/15"}`}
    />
    {error && <span className="text-xs text-red-600">{error}</span>}
  </label>
);
function Nav({ login }) {
  return (
    <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
      <Logo />
      <div className="hidden gap-7 text-sm font-semibold text-ink/70 md:flex">
        <a href="#about">About us</a>
        <a href="#features">How it works</a>
      </div>
      <div className="flex items-center gap-1">
        <CurrencySwitcher />
        <Btn plain onClick={login}>
          Login
        </Btn>
        <Btn onClick={() => go("/register")}>Get started</Btn>
      </div>
    </nav>
  );
}
function Login({ close, setToken }) {
  const [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [err, setErr] = useState("");
  async function submit(e) {
    e.preventDefault();
    let r = await fetch(`${API}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      }),
      d = await r.json();
    if (!r.ok) return setErr(d.detail);
    localStorage.token = d.access_token;
    setToken(d.access_token);
    close();
    go("/dashboard");
  }
  return (
    <div className="fixed inset-0 z-20 grid place-items-center bg-forest/40 p-4 backdrop-blur-sm">
      <form
        onSubmit={submit}
        className="w-full max-w-md rounded-3xl bg-white p-7 shadow-2xl"
      >
        <div className="flex justify-between">
          <div>
            <p className="text-sm font-bold text-sage">WELCOME BACK</p>
            <h2 className="text-3xl font-bold">Log in</h2>
          </div>
          <button type="button" className="text-2xl" onClick={close}>
            ×
          </button>
        </div>
        <div className="mt-6">
          <Field label="Email" value={email} set={setEmail} type="email" />
          <Field
            label="Password"
            value={password}
            set={setPassword}
            type="password"
          />
        </div>
        {err && <p className="mb-3 text-sm text-red-600">{err}</p>}
        <Btn type="submit">Log in</Btn>
      </form>
    </div>
  );
}
function Landing({ login }) {
  let cards = [
    [
      "♻",
      "Zero Waste",
      "Turn expiring pantry staples into the next best meal.",
    ],
    [
      "⌖",
      "Local Price Matching",
      "See the least expensive nearby source before you shop.",
    ],
    [
      "◌",
      "Macro/BMI Optimization",
      "Meals work with your routine, body and goal.",
    ],
  ];
  return (
    <>
      <Nav login={login} />
      <main>
        <section className="mx-auto grid max-w-7xl items-center gap-10 px-6 pb-20 pt-10 lg:grid-cols-[1.1fr_.9fr]">
          <div className="animate-rise">
            <p className="mb-4 inline-flex rounded-full bg-lime/50 px-4 py-2 text-sm font-bold text-forest">
              Food that fits your real life
            </p>
            <h1 className="text-5xl font-extrabold leading-[.98] tracking-[-.055em] text-forest sm:text-7xl">
              Eat smarter.
              <br />
              <span className="text-sage">Waste less.</span>
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-ink/70">
              Your pantry, health goals and neighborhood stores—finally working
              together in one gentle daily plan.
            </p>
            <div className="mt-8 flex gap-3">
              <Btn onClick={() => go("/register")}>Build my pantry plan →</Btn>
              <Btn
                plain
                onClick={() =>
                  document
                    .querySelector("#features")
                    .scrollIntoView({ behavior: "smooth" })
                }
              >
                Explore
              </Btn>
            </div>
          </div>
          <div className="rounded-[2rem] bg-forest p-5 shadow-2xl shadow-forest/25">
            <div className="rounded-[1.5rem] bg-cream p-5">
              <div className="flex justify-between">
                <b>Tuesday's plan</b>
                <span className="rounded-full bg-lime px-3 py-1 text-xs font-bold">
                  89% pantry match
                </span>
              </div>
              <div className="mt-5 rounded-2xl bg-white p-5">
                <p className="text-xs font-bold text-sage">LUNCH · 12 MIN</p>
                <h3 className="mt-1 text-xl font-bold">
                  Bright broccoli egg bowl
                </h3>
                <p className="mt-4 text-sm">
                  25g protein · 320 kcal ·{" "}
                  <b className="text-forest">$1.08 to buy</b>
                </p>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-xl bg-mint p-3">
                  <b>Use first</b>
                  <br />
                  Broccoli · 2 days
                </div>
                <div className="rounded-xl bg-lime/50 p-3">
                  <b>Closest store</b>
                  <br />
                  0.8 km away
                </div>
              </div>
            </div>
          </div>
        </section>
        <section id="about" className="bg-forest px-6 py-20 text-white">
          <div className="mx-auto grid max-w-7xl gap-12 md:grid-cols-2">
            <div>
              <p className="text-sm font-bold text-lime">WHY PANTRYWISE</p>
              <h2 className="mt-3 text-4xl font-bold">
                Built for the gap between good intentions and Tuesday night.
              </h2>
            </div>
            <p className="text-lg leading-8 text-white/70">
              We make the nourishing choice feel easier: first look at what you
              have, then match it to your needs, then find the most sensible
              local price for what’s missing.
            </p>
          </div>
        </section>
        <section id="features" className="mx-auto max-w-7xl px-6 py-20">
          <p className="text-sm font-bold text-sage">
            A MORE THOUGHTFUL KITCHEN
          </p>
          <h2 className="mt-2 text-4xl font-bold text-forest">
            Small choices, smarter system.
          </h2>
          <div className="mt-8 grid gap-5 md:grid-cols-3">
            {cards.map((c) => (
              <article
                key={c[1]}
                className="rounded-3xl border border-forest/10 bg-white p-7 shadow-sm"
              >
                <span className="grid h-12 w-12 place-items-center rounded-2xl bg-mint text-2xl">
                  {c[0]}
                </span>
                <h3 className="mt-6 text-xl font-bold">{c[1]}</h3>
                <p className="mt-2 leading-7 text-ink/65">{c[2]}</p>
              </article>
            ))}
          </div>
        </section>
      </main>
    </>
  );
}
function Address({ form, set, err }) {
  let [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!form.lat || !form.lon) set({ ...form, ...FALLBACK });
  }, []);
  async function search() {
    if (!form.address.trim()) return;
    setBusy(true);
    try {
      let r = await fetch(`${API}/location/geocode`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ address: form.address }),
        }),
        d = await r.json();
      set({ ...form, address: d.formatted_address, lat: d.lat, lon: d.lon });
    } catch {
      set({ ...form, ...FALLBACK });
    } finally {
      setBusy(false);
    }
  }
  function current() {
    if (!navigator.geolocation) return set({ ...form, ...FALLBACK });
    setBusy(true);
    navigator.geolocation.getCurrentPosition(
      (p) => {
        set({
          ...form,
          lat: p.coords.latitude,
          lon: p.coords.longitude,
          address: form.address || "Current device location",
        });
        setBusy(false);
      },
      () => {
        set({ ...form, ...FALLBACK });
        setBusy(false);
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 300000 },
    );
  }
  return (
    <div className="mb-4">
      <label className="block text-sm font-bold">
        Street address
        <input
          required
          value={form.address}
          onChange={(e) => set({ ...form, address: e.target.value })}
          placeholder="Type an address to find it"
          className="mt-1 w-full rounded-xl border border-forest/15 px-4 py-3 outline-none focus:ring-4 focus:ring-mint"
        />
      </label>
      <div className="mt-2 flex flex-wrap gap-2">
        <Btn plain onClick={search}>
          {busy ? "Finding…" : "Find address"}
        </Btn>
        <Btn plain onClick={current}>
          ⌖ Use My Current Location
        </Btn>
      </div>
      <span className="mt-2 block text-xs text-ink/55">
        Free OpenStreetMap address search · coordinates:{" "}
        {Number(form.lat).toFixed(4)}, {Number(form.lon).toFixed(4)}
      </span>
      {err && <span className="text-xs text-red-600">{err}</span>}
    </div>
  );
}
const options = {
  daily_routine: [
    ["desk", "Desk job / mostly sitting"],
    ["on_feet", "On feet / walking"],
    ["labor", "Heavy physical labor"],
  ],
  exercise_frequency: [
    ["0-1", "0–1 days"],
    ["2-3", "2–3 days"],
    ["4-5", "4–5 days"],
    ["6+", "6+ days"],
  ],
  exercise_intensity: [
    ["light", "Light cardio"],
    ["moderate", "Moderate weight training"],
    ["high", "High intensity"],
  ],
  daily_movement: [
    ["under_5000", "Under 5,000 steps"],
    ["5000_10000", "5,000–10,000 steps"],
    ["over_10000", "10,000+ steps"],
  ],
};
function Choice({ name, title, form, set }) {
  return (
    <div className="mb-6">
      <h3 className="font-bold">{title}</h3>
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {options[name].map(([v, l]) => (
          <button
            type="button"
            key={v}
            onClick={() => set({ ...form, [name]: v })}
            className={`rounded-xl border p-3 text-left text-sm font-semibold ${form[name] === v ? "border-forest bg-mint" : "border-forest/10 bg-white"}`}
          >
            {l}
          </button>
        ))}
      </div>
    </div>
  );
}
function Register({ setToken }) {
  let [step, setStep] = useState(1),
    [err, setErr] = useState({}),
    [busy, setBusy] = useState(false),
    [form, setForm] = useState({
      name: "",
      email: "",
      password: "",
      age: "",
      gender: "female",
      height_cm: "",
      weight_kg: "",
      address: "",
      lat: "",
      lon: "",
      weight_goal: "maintenance",
      daily_routine: "desk",
      exercise_frequency: "0-1",
      exercise_intensity: "light",
      daily_movement: "under_5000",
    }),
    put = (k) => (v) => setForm({ ...form, [k]: v });
  function next() {
    let e = {};
    [
      "name",
      "email",
      "password",
      "age",
      "height_cm",
      "weight_kg",
      "address",
    ].forEach((k) => !form[k] && (e[k] = "Required"));
    if (form.password.length && form.password.length < 8)
      e.password = "Use at least 8 characters";
    if (!form.lat || !form.lon)
      e.address = mapsKey
        ? "Choose an address from the Google suggestions."
        : "Latitude and longitude are required without Maps.";
    setErr(e);
    if (!Object.keys(e).length) setStep(2);
  }
  async function submit() {
    setBusy(true);
    let r = await fetch(`${API}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          age: +form.age,
          height_cm: +form.height_cm,
          weight_kg: +form.weight_kg,
          lat: +form.lat,
          lon: +form.lon,
        }),
      }),
      d = await r.json();
    setBusy(false);
    if (!r.ok)
      return setErr({ form: d.detail || "Account could not be created" });
    localStorage.token = d.access_token;
    setToken(d.access_token);
    go("/dashboard");
  }
  return (
    <main className="min-h-screen px-5 py-8">
      <div className="mx-auto max-w-2xl">
        <Logo />
        <section className="mt-10 rounded-[2rem] bg-white p-6 shadow-xl shadow-forest/10 sm:p-10">
          <header className="mb-8 flex items-center gap-3">
            <b className="grid h-9 w-9 place-items-center rounded-full bg-forest text-white">
              {step}
            </b>
            <div>
              <p className="text-sm font-bold text-sage">STEP {step} OF 2</p>
              <h1 className="text-2xl font-bold">
                {step === 1 ? "Account and address" : "Lifestyle assessment"}
              </h1>
            </div>
          </header>
          {step === 1 ? (
            <>
              <div className="grid gap-x-4 sm:grid-cols-2">
                <Field
                  label="Your name"
                  value={form.name}
                  set={put("name")}
                  error={err.name}
                />
                <Field
                  label="Email address"
                  type="email"
                  value={form.email}
                  set={put("email")}
                  error={err.email}
                />
                <Field
                  label="Password"
                  type="password"
                  value={form.password}
                  set={put("password")}
                  error={err.password}
                />
                <label className="mb-4 block text-sm font-bold">
                  Gender
                  <select
                    value={form.gender}
                    onChange={(e) => put("gender")(e.target.value)}
                    className="mt-1 w-full rounded-xl border border-forest/15 px-4 py-3"
                  >
                    <option value="female">Female</option>
                    <option value="male">Male</option>
                    <option value="other">
                      Non-binary / prefer not to say
                    </option>
                  </select>
                </label>
                <Field
                  label="Age"
                  type="number"
                  value={form.age}
                  set={put("age")}
                  error={err.age}
                />
                <Field
                  label="Height (cm)"
                  type="number"
                  value={form.height_cm}
                  set={put("height_cm")}
                  error={err.height_cm}
                />
                <Field
                  label="Weight (kg)"
                  type="number"
                  value={form.weight_kg}
                  set={put("weight_kg")}
                  error={err.weight_kg}
                />
                <label className="mb-4 block text-sm font-bold">
                  Goal
                  <select
                    value={form.weight_goal}
                    onChange={(e) => put("weight_goal")(e.target.value)}
                    className="mt-1 w-full rounded-xl border border-forest/15 px-4 py-3"
                  >
                    <option value="maintenance">Maintain</option>
                    <option value="deficit">Gentle deficit</option>
                    <option value="surplus">Build / surplus</option>
                  </select>
                </label>
              </div>
              <Address form={form} set={setForm} err={err.address} />
              {!mapsKey && (
                <div className="grid grid-cols-2 gap-3">
                  <Field
                    label="Latitude"
                    type="number"
                    value={form.lat}
                    set={put("lat")}
                  />
                  <Field
                    label="Longitude"
                    type="number"
                    value={form.lon}
                    set={put("lon")}
                  />
                </div>
              )}
              <Btn onClick={next}>Continue to lifestyle →</Btn>
            </>
          ) : (
            <>
              <p className="mb-7 text-ink/65">
                Four quick answers let us estimate your daily energy needs more
                accurately than a generic activity label.
              </p>
              <Choice
                name="daily_routine"
                title="Primary daily routine"
                form={form}
                set={setForm}
              />
              <Choice
                name="exercise_frequency"
                title="Weekly exercise frequency"
                form={form}
                set={setForm}
              />
              <Choice
                name="exercise_intensity"
                title="Exercise intensity"
                form={form}
                set={setForm}
              />
              <Choice
                name="daily_movement"
                title="Daily movement level"
                form={form}
                set={setForm}
              />
              {err.form && (
                <p className="mb-3 text-sm text-red-600">{err.form}</p>
              )}
              <div className="flex justify-between">
                <Btn plain onClick={() => setStep(1)}>
                  ← Back
                </Btn>
                <Btn onClick={submit}>
                  {busy ? "Creating…" : "Create my plan →"}
                </Btn>
              </div>
            </>
          )}
        </section>
      </div>
    </main>
  );
}
function Dashboard({ token, setToken }) {
  let [profile, setProfile] = useState(),
    [recipes, setRecipes] = useState([]),
    [plan, setPlan] = useState(),
    h = { Authorization: `Bearer ${token}` };
  useEffect(() => {
    Promise.all([
      fetch(`${API}/nutrition/profile`, { headers: h }),
      fetch(`${API}/recipes/generate-smart`, { method: "POST", headers: h }),
    ]).then(async ([p, r]) => {
      if (!p.ok) {
        localStorage.removeItem("token");
        setToken("");
        return go("/");
      }
      setProfile(await p.json());
      setRecipes(await r.json());
    });
  }, []);
  async function source(id) {
    setPlan(
      await (
        await fetch(`${API}/shopping-list/sourcing?recipe_id=${id}`, {
          headers: h,
        })
      ).json(),
    );
  }
  return (
    <main className="min-h-screen">
      <nav className="mx-auto flex max-w-7xl justify-between px-6 py-5">
        <Logo />
        <button
          onClick={() => {
            localStorage.removeItem("token");
            setToken("");
            go("/");
          }}
          className="font-bold text-ink/60"
        >
          Log out
        </button>
      </nav>
      <div className="mx-auto max-w-7xl px-6 py-8">
        <p className="text-sm font-bold text-sage">YOUR HEALTH-LED PANTRY</p>
        <h1 className="text-4xl font-bold text-forest">
          A good next meal is close by.
        </h1>
        {profile && (
          <section className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              [profile.bmi, `BMI · ${profile.weight_status}`],
              [profile.daily_calories, "daily calories"],
              [`${profile.protein_g}g`, "protein target"],
              [`${profile.carbs_g}g / ${profile.fat_g}g`, "carbs / fats"],
            ].map((x) => (
              <article
                className="rounded-2xl bg-white p-5 shadow-sm"
                key={x[1]}
              >
                <b className="block text-2xl text-forest">{x[0]}</b>
                <span className="text-sm text-ink/55">{x[1]}</span>
              </article>
            ))}
          </section>
        )}
        <section className="mt-10 grid gap-4">
          {recipes.map((r) => (
            <article
              key={r.id}
              className="flex flex-col justify-between gap-5 rounded-3xl bg-white p-6 shadow-sm sm:flex-row"
            >
              <div>
                <span className="rounded-full bg-mint px-3 py-1 text-xs font-bold text-forest">
                  {r.pantry_match_percent}% pantry match
                </span>
                <h2 className="mt-3 text-2xl font-bold">{r.title}</h2>
                <p className="mt-1 text-sm text-ink/60">
                  {r.calories} kcal · {r.protein_g}g protein ·{" "}
                  {r.missing_ingredients.length
                    ? r.missing_ingredients
                        .map((i) => i.ingredient_name)
                        .join(", ")
                    : "nothing missing"}
                </p>
              </div>
              <div className="text-right">
                <b className="block text-2xl text-forest">
                  ${r.estimated_missing_cost.toFixed(2)}
                </b>
                <small>local estimate</small>
                <br />
                <Btn onClick={() => source(r.id)}>See sourcing</Btn>
              </div>
            </article>
          ))}
        </section>
        {plan && (
          <section className="mt-8 rounded-3xl bg-forest p-7 text-white">
            <h2 className="text-2xl font-bold">
              {plan.recipe_title} · ${plan.total_cost.toFixed(2)}
            </h2>
            {plan.items.map((i) => (
              <div
                className="mt-3 flex justify-between rounded-xl bg-white/10 p-4 text-sm"
                key={i.ingredient_name}
              >
                <b>
                  {i.ingredient_name} · {i.quantity}
                  {i.unit}
                </b>
                <span>
                  {i.best_option
                    ? `${i.best_option.store_name}, ${i.best_option.distance_km} km · $${i.best_option.estimated_cost.toFixed(2)}`
                    : "No nearby option"}
                </span>
              </div>
            ))}
          </section>
        )}
      </div>
    </main>
  );
}
function Settings({ profile, headers, onSave, close }) {
  let [form, setForm] = useState(profile),
    [busy, setBusy] = useState(false);
  let put = (k) => (v) => setForm({ ...form, [k]: v });
  let options = [
    [
      "daily_routine",
      "Daily routine",
      [
        ["desk", "Mostly sitting"],
        ["on_feet", "On feet / walking"],
        ["labor", "Physical labor"],
      ],
    ],
    [
      "exercise_frequency",
      "Exercise days",
      [
        ["0-1", "0–1"],
        ["2-3", "2–3"],
        ["4-5", "4–5"],
        ["6+", "6+"],
      ],
    ],
    [
      "exercise_intensity",
      "Exercise intensity",
      [
        ["light", "Light"],
        ["moderate", "Moderate"],
        ["high", "High intensity"],
      ],
    ],
    [
      "daily_movement",
      "Daily movement",
      [
        ["under_5000", "Under 5k steps"],
        ["5000_10000", "5k–10k steps"],
        ["over_10000", "10k+ steps"],
      ],
    ],
  ];
  async function save(e) {
    e.preventDefault();
    setBusy(true);
    let r = await fetch(`${API}/auth/profile`, {
      method: "PATCH",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({
        age: +form.age,
        height_cm: +form.height_cm,
        weight_kg: +form.weight_kg,
        address: form.address,
        daily_routine: form.daily_routine,
        exercise_frequency: form.exercise_frequency,
        exercise_intensity: form.exercise_intensity,
        daily_movement: form.daily_movement,
        weight_goal: form.weight_goal,
      }),
    });
    if (r.ok) onSave(await r.json());
    setBusy(false);
    close();
  }
  return (
    <div className="fixed inset-0 z-20 overflow-auto bg-forest/40 p-4 backdrop-blur-sm">
      <form
        onSubmit={save}
        className="mx-auto my-8 max-w-2xl rounded-3xl bg-white p-7 shadow-2xl"
      >
        <div className="flex justify-between">
          <div>
            <p className="text-sm font-bold text-sage">SETTINGS</p>
            <h2 className="text-3xl font-bold">Health profile & location</h2>
          </div>
          <button type="button" onClick={close} className="text-2xl">
            ×
          </button>
        </div>
        <div className="mt-6 grid gap-x-4 sm:grid-cols-2">
          <Field label="Age" type="number" value={form.age} set={put("age")} />
          <Field
            label="Height (cm)"
            type="number"
            value={form.height_cm}
            set={put("height_cm")}
          />
          <Field
            label="Current weight (kg)"
            type="number"
            value={form.weight_kg}
            set={put("weight_kg")}
          />
          <label className="mb-4 block text-sm font-bold">
            Goal
            <select
              value={form.weight_goal}
              onChange={(e) => put("weight_goal")(e.target.value)}
              className="mt-1 w-full rounded-xl border border-forest/15 px-4 py-3"
            >
              <option value="maintenance">Maintain</option>
              <option value="deficit">Gentle deficit</option>
              <option value="surplus">Build / surplus</option>
            </select>
          </label>
        </div>
        <Field
          label="Street address"
          value={form.address}
          set={put("address")}
        />
        <div className="mt-2 grid gap-4 sm:grid-cols-2">
          {options.map(([key, label, items]) => (
            <label className="block text-sm font-bold" key={key}>
              {label}
              <select
                value={form[key]}
                onChange={(e) => put(key)(e.target.value)}
                className="mt-1 w-full rounded-xl border border-forest/15 px-4 py-3"
              >
                {items.map((x) => (
                  <option key={x[0]} value={x[0]}>
                    {x[1]}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </div>
        <div className="mt-7 flex justify-end gap-2">
          <Btn plain onClick={close}>
            Cancel
          </Btn>
          <Btn type="submit">{busy ? "Saving…" : "Save & recalculate"}</Btn>
        </div>
      </form>
    </div>
  );
}
function ExplorerDashboard({ token, setToken }) {
  let [profile, setProfile] = useState(),
    [user, setUser] = useState(),
    [recipes, setRecipes] = useState([]),
    [filter, setFilter] = useState("All"),
    [shown, setShown] = useState(6),
    [settings, setSettings] = useState(false),
    [plan, setPlan] = useState(),
    h = { Authorization: `Bearer ${token}` };
  let load = async (choice = filter) => {
    let tag = ["High Protein", "Budget Friendly"].includes(choice)
        ? choice
        : null,
      category = tag ? "All" : choice;
    let r = await fetch(`${API}/recipes/generate-smart`, {
      method: "POST",
      headers: { ...h, "Content-Type": "application/json" },
      body: JSON.stringify({ category, tag, limit: 24 }),
    });
    setRecipes(await r.json());
    setShown(6);
  };
  useEffect(() => {
    Promise.all([
      fetch(`${API}/nutrition/profile`, { headers: h }),
      fetch(`${API}/auth/profile`, { headers: h }),
    ]).then(async ([p, u]) => {
      if (!p.ok) {
        localStorage.removeItem("token");
        setToken("");
        return go("/");
      }
      setProfile(await p.json());
      setUser(await u.json());
      load("All");
    });
  }, []);
  async function source(id) {
    setPlan(
      await (
        await fetch(`${API}/shopping-list/sourcing?recipe_id=${id}`, {
          headers: h,
        })
      ).json(),
    );
  }
  function select(x) {
    setFilter(x);
    load(x);
  }
  let bmiColor =
    profile?.bmi < 18.5
      ? "bg-sky-400"
      : profile?.bmi < 25
        ? "bg-emerald-500"
        : profile?.bmi < 30
          ? "bg-amber-400"
          : "bg-rose-500";
  return (
    <main className="min-h-screen">
      <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
        <Logo />
        <div className="flex gap-2">
          <Btn plain onClick={() => setSettings(true)}>
            Edit health profile & location
          </Btn>
          <button
            onClick={() => {
              localStorage.removeItem("token");
              setToken("");
              go("/");
            }}
            className="text-sm font-bold text-ink/60"
          >
            Log out
          </button>
        </div>
      </nav>
      <div className="mx-auto max-w-7xl px-6 py-8">
        <p className="text-sm font-bold text-sage">YOUR HEALTH-LED PANTRY</p>
        <h1 className="text-4xl font-bold text-forest">
          Your next meal, made practical.
        </h1>
        {profile && (
          <section className="mt-8 grid gap-4 lg:grid-cols-[1.35fr_1fr]">
            <article className="rounded-3xl bg-white p-6 shadow-sm">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-bold text-sage">BMI TRACKER</p>
                  <b className="mt-1 block text-5xl text-forest">
                    {profile.bmi}
                  </b>
                  <span className="font-semibold capitalize text-ink/60">
                    {profile.weight_status}
                  </span>
                </div>
                <div className="rounded-2xl bg-mint p-3 text-sm">
                  <b>{profile.current_weight_kg} kg</b>
                  <br />
                  <span className="text-ink/60">current</span>
                </div>
              </div>
              <div className="mt-6">
                <div className="flex justify-between text-xs font-bold text-ink/50">
                  <span>Underweight</span>
                  <span>Normal</span>
                  <span>Overweight</span>
                  <span>Obese</span>
                </div>
                <div className="mt-2 h-3 rounded-full bg-slate-100">
                  <div
                    className={`h-3 rounded-full ${bmiColor}`}
                    style={{
                      width: `${Math.min(100, Math.max(8, (profile.bmi / 40) * 100))}%`,
                    }}
                  />
                </div>
              </div>
              <div className="mt-5 flex justify-between rounded-2xl bg-cream p-4 text-sm">
                <span>
                  Target weight <b>{profile.target_weight_kg} kg</b>
                </span>
                <span>
                  Goal: <b className="capitalize">{user?.weight_goal}</b>
                </span>
              </div>
            </article>
            <article className="rounded-3xl bg-forest p-6 text-white shadow-sm">
              <p className="text-sm font-bold text-lime">DAILY ENERGY</p>
              <b className="mt-1 block text-5xl">{profile.daily_calories}</b>
              <span className="text-white/65">TDEE calories</span>
              <div className="mt-6 grid grid-cols-3 gap-2 text-center text-xs">
                <div className="rounded-xl bg-white/10 p-3">
                  <b className="block text-lg">{profile.protein_g}g</b>Protein
                </div>
                <div className="rounded-xl bg-white/10 p-3">
                  <b className="block text-lg">{profile.carbs_g}g</b>Carbs
                </div>
                <div className="rounded-xl bg-white/10 p-3">
                  <b className="block text-lg">{profile.fat_g}g</b>Fats
                </div>
              </div>
            </article>
          </section>
        )}
        <section className="mt-12">
          <div className="flex flex-col justify-between gap-4 sm:flex-row">
            <div>
              <p className="text-sm font-bold text-sage">RECIPE EXPLORER</p>
              <h2 className="text-3xl font-bold text-forest">
                Ideas shaped around your pantry
              </h2>
            </div>
            <span className="self-end text-sm font-semibold text-ink/60">
              {recipes.length} matches
            </span>
          </div>
          <div className="mt-5 flex gap-2 overflow-x-auto pb-2">
            {[
              "All",
              "Breakfast",
              "Lunch",
              "Dinner",
              "Snacks",
              "High Protein",
              "Budget Friendly",
            ].map((x) => (
              <button
                onClick={() => select(x)}
                key={x}
                className={`whitespace-nowrap rounded-full px-4 py-2 text-sm font-bold ${filter === x ? "bg-forest text-white" : "bg-white text-ink/65 shadow-sm"}`}
              >
                {x}
              </button>
            ))}
          </div>
          <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {recipes.slice(0, shown).map((r) => (
              <article
                key={r.id}
                className="flex min-h-64 flex-col rounded-3xl bg-white p-5 shadow-sm"
              >
                <div className="flex justify-between gap-2">
                  <span className="rounded-full bg-mint px-3 py-1 text-xs font-bold text-forest">
                    {r.meal_type}
                  </span>
                  <span className="text-xs font-bold text-sage">
                    {r.pantry_match_percent}% pantry
                  </span>
                </div>
                <h3 className="mt-5 text-2xl font-bold">{r.title}</h3>
                <p className="mt-2 text-sm text-ink/60">
                  {r.missing_ingredients.length
                    ? r.missing_ingredients
                        .map((i) => i.ingredient_name)
                        .join(", ")
                    : "Everything is in your pantry."}
                </p>
                <div className="mt-auto pt-5">
                  <div className="flex flex-wrap gap-2 text-xs font-semibold">
                    <span className="rounded-lg bg-cream px-2 py-1">
                      ◷ {r.prep_time} min
                    </span>
                    <span className="rounded-lg bg-cream px-2 py-1">
                      P {r.protein_g}g · C {r.carbs_g}g · F {r.fat_g}g
                    </span>
                  </div>
                  <div className="mt-3 flex items-center justify-between">
                    <span className="text-sm font-bold text-forest">
                      ${r.estimated_missing_cost.toFixed(2)} local
                    </span>
                    <Btn onClick={() => source(r.id)}>Source</Btn>
                  </div>
                </div>
              </article>
            ))}
          </div>
          {shown < recipes.length && (
            <div className="mt-7 text-center">
              <Btn plain onClick={() => setShown(shown + 6)}>
                Show more recipes ↓
              </Btn>
            </div>
          )}
        </section>
        {plan && (
          <section className="mt-8 rounded-3xl bg-forest p-7 text-white">
            <h2 className="text-2xl font-bold">
              {plan.recipe_title} · ${plan.total_cost.toFixed(2)}
            </h2>
            {plan.items.map((i) => (
              <div
                className="mt-3 flex justify-between rounded-xl bg-white/10 p-4 text-sm"
                key={i.ingredient_name}
              >
                <b>
                  {i.ingredient_name} · {i.quantity}
                  {i.unit}
                </b>
                <span>
                  {i.best_option
                    ? `${i.best_option.store_name}, ${i.best_option.distance_km} km · $${i.best_option.estimated_cost.toFixed(2)}`
                    : "No nearby option"}
                </span>
              </div>
            ))}
          </section>
        )}
      </div>
      {settings && user && (
        <Settings
          profile={user}
          headers={h}
          close={() => setSettings(false)}
          onSave={(updated) => {
            setProfile(updated);
            fetch(`${API}/auth/profile`, { headers: h })
              .then((r) => r.json())
              .then(setUser);
          }}
        />
      )}
    </main>
  );
}
function SourcingPlan({ plan }) {
  const { formatPrice, configureCurrency } = useCurrency();
  useEffect(() => configureCurrency(plan), [plan]);
  return (
    <section className="mt-8 rounded-3xl bg-forest p-7 text-white">
      <p className="text-sm font-bold text-lime">LOCAL SOURCING</p>
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <h2 className="text-2xl font-bold">
          {plan.recipe_title} · {formatPrice(plan.total_cost)}
        </h2>
        <CurrencySwitcher />
      </div>
      <div className="mt-4 grid gap-3">
        {(plan.items || []).map((i) => {
          let store = i.best_option || {},
            name = store.store_name || "Nearby grocery store",
            address = store.address || "Location details unavailable",
            distance = Number(store.distance_km),
            cost = Number(store.estimated_cost),
            destination = encodeURIComponent(`${name} ${address}`);
          return (
            <article
              className="rounded-xl bg-white/10 p-4"
              key={i.ingredient_name}
            >
              <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
                <div>
                  <b>
                    {i.ingredient_name} · {i.quantity}
                    {i.unit}
                  </b>
                  <p className="mt-1 text-sm text-white/75">
                    {name} ·{" "}
                    {Number.isFinite(distance)
                      ? `${distance.toFixed(1)} km`
                      : "Distance unavailable"}{" "}
                    ·{" "}
                    {Number.isFinite(cost)
                      ? formatPrice(cost)
                      : "Cost unavailable"}
                  </p>
                </div>
                <a
                  href={`https://www.google.com/maps/dir/?api=1&destination=${destination}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex shrink-0 items-center justify-center rounded-xl bg-lime px-4 py-2 text-sm font-bold text-forest transition hover:bg-white"
                >
                  Navigate ↗
                </a>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
ExplorerDashboard = function ({ token, setToken }) {
  const { formatPrice, configureCurrency } = useCurrency();
  let [profile, setProfile] = useState(),
    [recipes, setRecipes] = useState([]),
    [plan, setPlan] = useState(),
    [filter, setFilter] = useState("All"),
    [shown, setShown] = useState(6),
    h = { Authorization: `Bearer ${token}` };
  async function load(choice = "All") {
    let tag =
        choice === "High Protein" || choice === "Budget Friendly"
          ? choice
          : null,
      r = await fetch(`${API}/recipes/generate-smart`, {
        method: "POST",
        headers: { ...h, "Content-Type": "application/json" },
        body: JSON.stringify({
          category: tag ? "All" : choice,
          tag,
          limit: 24,
        }),
      });
    setRecipes(await r.json());
    setShown(6);
  }
  useEffect(() => {
    fetch(`${API}/nutrition/profile`, { headers: h })
      .then((r) => r.json())
      .then(setProfile);
    fetch(`${API}/auth/profile`, { headers: h })
      .then((r) => r.json())
      .then(configureCurrency);
    load();
  }, []);
  async function source(id) {
    let r = await fetch(`${API}/shopping-list/sourcing?recipe_id=${id}`, {
      headers: h,
    });
    const sourcedPlan = await r.json();
    configureCurrency(sourcedPlan);
    setPlan(sourcedPlan);
  }
  let pills = [
    "All",
    "Breakfast",
    "Lunch",
    "Dinner",
    "Snacks",
    "High Protein",
    "Budget Friendly",
  ];
  return (
    <main className="min-h-screen">
      <nav className="mx-auto flex max-w-7xl justify-between px-6 py-5">
        <Logo />
        <GlobalSearch headers={h} apiUrl={API} formatPrice={formatPrice} />
        <div className="flex items-center gap-2">
          <CurrencySwitcher />
          <button
          onClick={() => {
            localStorage.removeItem("token");
            setToken("");
            go("/");
          }}
          className="font-bold text-ink/60"
        >
          Log out
          </button>
        </div>
      </nav>
      <div className="mx-auto max-w-7xl px-6 py-8">
        <h1 className="text-4xl font-bold text-forest">Your smart pantry</h1>
        {profile && (
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <article className="rounded-3xl bg-white p-6 shadow-sm">
              <p className="text-sm font-bold text-sage">BMI TRACKER</p>
              <b className="text-5xl text-forest">{profile.bmi}</b>
              <div className="mt-4 h-3 rounded-full bg-slate-100">
                <div
                  className={
                    profile.bmi < 25
                      ? "h-3 rounded-full bg-emerald-500"
                      : "h-3 rounded-full bg-amber-400"
                  }
                  style={{
                    width: `${Math.min(100, (profile.bmi / 40) * 100)}%`,
                  }}
                />
              </div>
            </article>
            <article className="rounded-3xl bg-forest p-6 text-white">
              <p className="text-sm font-bold text-lime">DAILY TDEE</p>
              <b className="text-4xl">{profile.daily_calories}</b>
              <p className="mt-3 text-sm">
                Protein {profile.protein_g}g · Carbs {profile.carbs_g}g · Fats{" "}
                {profile.fat_g}g
              </p>
            </article>
          </div>
        )}
        <div className="mt-10 flex gap-2 overflow-x-auto pb-2">
          {pills.map((p) => (
            <button
              key={p}
              onClick={() => {
                setFilter(p);
                load(p);
              }}
              className={
                filter === p
                  ? "whitespace-nowrap rounded-full bg-forest px-4 py-2 text-sm font-bold text-white"
                  : "whitespace-nowrap rounded-full bg-white px-4 py-2 text-sm font-bold text-ink/65"
              }
            >
              {p}
            </button>
          ))}
        </div>
        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {recipes.slice(0, shown).map((r) => (
            <RecipeCard key={r.id} recipe={r} headers={h} apiUrl={API} formatPrice={formatPrice} />
          ))}
        </div>
        {shown < recipes.length && (
          <div className="mt-6 text-center">
            <Btn plain onClick={() => setShown(shown + 6)}>
              Show more
            </Btn>
          </div>
        )}
        {plan && <SourcingPanel recipeId={plan.recipe_id} plan={plan} formatPrice={formatPrice} headers={h} apiUrl={API} />}
        <div className="mt-8"><Pantry headers={h} apiUrl={API} /></div>
        <div className="mt-8"><WeeklyPlanner recipes={recipes} formatPrice={formatPrice} headers={h} apiUrl={API} /></div>
      </div>
    </main>
  );
};
function AppRoutes() {
  let [path, setPath] = useState(location.pathname),
    [token, setToken] = useState(localStorage.token || ""),
    [modal, setModal] = useState(false);
  useEffect(() => {
    let f = () => setPath(location.pathname);
    addEventListener("popstate", f);
    return () => removeEventListener("popstate", f);
  }, []);
  return (
    <>
      {path === "/register" ? (
        <Register setToken={setToken} />
      ) : path === "/dashboard" && token ? (
        <ExplorerDashboard token={token} setToken={setToken} />
      ) : (
        <Landing login={() => setModal(true)} />
      )}{" "}
      {modal && <Login close={() => setModal(false)} setToken={setToken} />}
    </>
  );
}
function App() {
  return <CurrencyProvider><AppRoutes /></CurrencyProvider>;
}
createRoot(document.getElementById("root")).render(<App />);
