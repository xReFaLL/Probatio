import type { Trade } from "@/lib/types";
import { fmtCurrency, fmtDate } from "@/lib/format";

export default function TradesTable({ trades }: { trades: Trade[] }) {
  if (trades.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-bg-panel p-4 text-sm text-ink-faint">
        Aucun trade sur la période — la stratégie n&apos;a jamais été en position.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-bg-panel">
      <h3 className="px-4 pt-4 text-xs font-semibold uppercase tracking-wide text-ink-muted">
        Trades ({trades.length})
      </h3>
      <div className="max-h-72 overflow-y-auto px-2 pb-2">
        <table className="w-full text-left text-sm">
          <thead className="sticky top-0 bg-bg-panel text-[11px] uppercase text-ink-faint">
            <tr>
              <th className="px-2 py-2 font-medium">Sens</th>
              <th className="px-2 py-2 font-medium">Entrée</th>
              <th className="px-2 py-2 font-medium">Sortie</th>
              <th className="px-2 py-2 text-right font-medium">Quantité</th>
              <th className="px-2 py-2 text-right font-medium">P&amp;L</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((t, idx) => (
              <tr key={idx} className="border-t border-border-subtle">
                <td className="px-2 py-1.5">
                  <span
                    className={`rounded px-1.5 py-0.5 text-[11px] font-medium ${
                      t.side === "long" ? "bg-up/10 text-up" : "bg-down/10 text-down"
                    }`}
                  >
                    {t.side}
                  </span>
                </td>
                <td className="tabular px-2 py-1.5 font-mono text-xs text-ink-muted">
                  {fmtDate(t.entry_time)} · {fmtCurrency(t.entry_price)}
                </td>
                <td className="tabular px-2 py-1.5 font-mono text-xs text-ink-muted">
                  {fmtDate(t.exit_time)} · {fmtCurrency(t.exit_price)}
                </td>
                <td className="tabular px-2 py-1.5 text-right font-mono text-xs">
                  {t.quantity.toFixed(4)}
                </td>
                <td
                  className={`tabular px-2 py-1.5 text-right font-mono text-xs font-semibold ${
                    t.pnl >= 0 ? "text-up" : "text-down"
                  }`}
                >
                  {t.pnl >= 0 ? "+" : ""}
                  {fmtCurrency(t.pnl)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}