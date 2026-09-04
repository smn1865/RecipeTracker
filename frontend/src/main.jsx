import React, { createContext, useContext, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { BrandMark } from "./components/Header";
import { Dashboard } from "./pages/Dashboard";
import { ProfileSettings } from "./pages/ProfileSettings";
import { Register } from "./pages/Register";
import { Welcome } from "./pages/Welcome";
import "./styles.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
const CurrencyContext = createContext(null);

function navigate(path) {
  history.pushState({}, "", path);
  dispatchEvent(new PopStateEvent("popstate"));
}

function CurrencyProvider({ children }) {
  const [currencyMode, setCurrencyMode] = useState("LOCAL");
  const [currency, setCurrency] = useState({ localCurrency: "AMD", localSymbol: "֏", usdToLocalRate: 388 });
  const configureCurrency = (data = {}) => setCurrency({
    localCurrency: data.local_currency || "AMD",
    localSymbol: data.local_currency_symbol || "֏",
    usdToLocalRate: Number(data.usd_to_local_rate || 388),
  });
  const formatPrice = (usdAmount) => {
    const amount = Number(usdAmount || 0);
    return currencyMode === "LOCAL"
      ? `${(amount * currency.usdToLocalRate).toLocaleString(undefined, { maximumFractionDigits: 0 })} ${currency.localSymbol}`
      : `$${amount.toFixed(2)}`;
  };
  return <CurrencyContext.Provider value={{ currencyMode, setCurrencyMode, ...currency, configureCurrency, formatPrice }}>{children}</CurrencyContext.Provider>;
}

function CurrencySwitcher() {
  const { currencyMode, setCurrencyMode, localCurrency, localSymbol } = useContext(CurrencyContext);
  return <div className="inline-flex rounded-full bg-white/70 p-1 text-xs font-bold shadow-sm">
    <button onClick={() => setCurrencyMode("LOCAL")} className={currencyMode === "LOCAL" ? "rounded-full bg-forest px-3 py-2 text-lime" : "px-3 py-2 text-ink/50"}>{localCurrency} {localSymbol}</button>
    <button onClick={() => setCurrencyMode("USD")} className={currencyMode === "USD" ? "rounded-full bg-forest px-3 py-2 text-lime" : "px-3 py-2 text-ink/50"}>USD $</button>
  </div>;
}

function Login({ onClose, onSuccess }) {
  const [email, setEmail] = useState(""), [password, setPassword] = useState(""), [error, setError] = useState(""), [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError("");
    const response = await fetch(`${API}/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) });
    const data = await response.json(); setBusy(false);
    if (!response.ok) return setError(data.detail || "Could not log in.");
    onSuccess(data.access_token);
  }
  return <div className="fixed inset-0 z-50 grid place-items-center bg-forest/50 p-4 backdrop-blur-sm"><form onSubmit={submit} className="w-full max-w-md rounded-[2rem] bg-white p-7 shadow-2xl"><div className="flex items-start justify-between"><BrandMark onClick={() => {}}/><button type="button" onClick={onClose} className="text-2xl">×</button></div><h2 className="mt-7 text-3xl font-bold text-forest">Welcome back</h2><p className="mt-1 text-sm text-ink/50">Continue your pantry and weekly diet plan.</p><label className="mt-6 block text-sm font-bold">Email<input required type="email" value={email} onChange={e => setEmail(e.target.value)} className="mt-1 w-full rounded-xl border border-forest/10 px-4 py-3"/></label><label className="mt-4 block text-sm font-bold">Password<input required type="password" value={password} onChange={e => setPassword(e.target.value)} className="mt-1 w-full rounded-xl border border-forest/10 px-4 py-3"/></label>{error && <p className="mt-3 text-sm font-semibold text-amber-700">{error}</p>}<button disabled={busy} className="mt-6 w-full rounded-xl bg-forest px-5 py-3 font-bold text-white disabled:opacity-50">{busy ? "Logging in…" : "Login"}</button></form></div>;
}

function AppRoutes() {
  const [path, setPath] = useState(location.pathname), [token, setToken] = useState(localStorage.token || ""), [loginOpen, setLoginOpen] = useState(false);
  const currency = useContext(CurrencyContext);
  useEffect(() => { const listener = () => setPath(location.pathname); addEventListener("popstate", listener); return () => removeEventListener("popstate", listener); }, []);
  function authenticate(value) { localStorage.token = value; setToken(value); setLoginOpen(false); navigate("/dashboard"); }
  function logout() { localStorage.removeItem("token"); setToken(""); navigate("/"); }
  const switcher = <CurrencySwitcher />;
  let page;
  if (path === "/register") page = <Register apiUrl={API} onHome={() => navigate("/")} onSuccess={authenticate}/>;
  else if (path === "/profile" && token) page = <ProfileSettings apiUrl={API} headers={{ Authorization: `Bearer ${token}` }} onBack={() => navigate("/dashboard")} onLogout={logout} currencySwitcher={switcher}/>;
  else if (path === "/dashboard" && token) page = <Dashboard apiUrl={API} token={token} onHome={() => navigate("/dashboard")} onProfile={() => navigate("/profile")} onLogout={logout} formatPrice={currency.formatPrice} configureCurrency={currency.configureCurrency} currencySwitcher={switcher}/>;
  else page = <Welcome onLogin={() => setLoginOpen(true)} onRegister={() => navigate("/register")} currencySwitcher={switcher}/>;
  return <>{page}{loginOpen && <Login onClose={() => setLoginOpen(false)} onSuccess={authenticate}/>}</>;
}

function App() {
  return <CurrencyProvider><AppRoutes/></CurrencyProvider>;
}

createRoot(document.getElementById("root")).render(<App/>);
