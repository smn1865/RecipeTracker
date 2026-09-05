export function StoreComparison({ assignment, ingredient, formatPrice, dark = false }) {
  const options = ingredient?.store_options || [];
  const surface = dark ? "border-white/10 bg-white/5" : "border-slate-200 bg-white";
  const muted = dark ? "text-white/55" : "text-slate-600";
  return <details className={`group rounded-2xl border ${surface}`}>
    <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-3 p-4">
      <div><b className="capitalize">{assignment.ingredient_name}</b><small className={`ml-2 ${muted}`}>Need {assignment.quantity}{assignment.unit}</small></div>
      <div className="flex items-center gap-3"><span className="rounded-full bg-amber-500 px-3 py-1 text-xs font-bold text-zinc-900">{assignment.branch_name || assignment.store_name} · {formatPrice(assignment.estimated_cost_usd)}</span><span className={`text-xs font-bold ${dark ? "text-emerald-400" : "text-emerald-700"}`}>Compare {Math.min(3,options.length)} Stores ▾</span></div>
    </summary>
    <div className={`grid gap-3 border-t p-4 sm:grid-cols-3 ${dark ? "border-white/10" : "border-slate-200"}`}>
      {options.map((store,index)=><article key={`${assignment.ingredient_name}-${store.store_id}`} className={`rounded-xl p-3 ${dark ? "bg-zinc-900" : "bg-slate-100"}`}>
        <div className="flex items-start justify-between gap-2"><b className="text-sm">{store.branch_name || store.store_name}</b>{index===0&&<span className="rounded-full bg-emerald-700 px-2 py-1 text-[10px] font-bold text-white">Best</span>}</div>
        <b className="mt-2 block text-amber-500">{formatPrice(store.extended_price_usd)}</b>
        <p className={`text-xs ${muted}`}>{store.packages_needed} × {store.package_size}{store.package_unit} · {store.distance_km} km</p>
        <p className={`mt-1 text-[11px] ${muted}`}>{store.street_address || store.address}</p>
        <a href={store.maps_url || store.navigation_url} target="_blank" rel="noopener noreferrer" className={`mt-3 inline-block rounded-lg px-3 py-2 text-xs font-bold text-white ${dark ? "bg-emerald-600" : "bg-emerald-700"}`}>Navigate ↗</a>
      </article>)}
    </div>
  </details>;
}
