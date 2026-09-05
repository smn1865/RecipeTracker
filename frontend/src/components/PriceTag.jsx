export function PriceTag({ totalUsd, unitUsd, formatPrice }) {
  return <div className="inline-flex items-center gap-2 rounded-lg bg-slate-100 px-2 py-1 text-xs font-bold text-emerald-700"><span>{formatPrice(totalUsd)}</span>{unitUsd != null && <span className="text-emerald-600">({formatPrice(unitUsd)} / kg)</span>}</div>;
}
