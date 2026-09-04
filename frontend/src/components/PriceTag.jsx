export function PriceTag({ totalUsd, unitUsd, formatPrice }) {
  return <div className="inline-flex items-center gap-2 rounded-lg bg-mint px-2 py-1 text-xs font-bold text-forest"><span>{formatPrice(totalUsd)}</span>{unitUsd != null && <span className="text-sage">({formatPrice(unitUsd)} / kg)</span>}</div>;
}
