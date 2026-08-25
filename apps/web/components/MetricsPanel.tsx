import type { Metrics } from "@/lib/types";
import { fmtCurrency, fmtNumber, fmtPct } from "@/lib/format";

export default function MetricsPanel({ metrics }: { metrics: Metrics }) {
  const cards: { label: string; value: string; tone?: "up" | "down" }[] = [
    {
      label: "Equity finale",
      value: fmtCurrency(metrics.final_equity),
    },
    { label: "Sharpe", value: fmtNumber(metrics.sharpe) },
    { label: "Sortino", value: fmtNumber(metrics.sortino) },
    {
      label: "Max drawdown",
      value: fmtPct(metrics.max_drawdown),
      tone: "down",
    },
    { label: "Taux de réussite", value: fmtPct(metrics.win_rate) },
    {
      label: "Profit factor",
      value: metrics.profit_factor === null ? "∞ (aucun trade perdant)" : fmtNumber(metrics.profit_factor),
    },
    { label: "Trades", value: String(metrics.total_trades) },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {cards.map((c) => (
        <div key={c.label} className="rounded-lg border border-border bg-bg-panel p-3">
          <div className="text-[11px] uppercase tracking-wide text-ink-faint">{c.label}</div>
          <div
            className={`tabular mt-1 font-mono text-lg ${
              c.tone === "down" ? "text-down" : c.tone === "up" ? "text-up" : "text-ink"
            }`}
          >
            {c.value}
          </div>
        </div>
      ))}
    </div>
  );
}