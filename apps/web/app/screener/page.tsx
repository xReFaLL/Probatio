"use client";

import { useEffect, useMemo, useState } from "react";
import { ApiError, getInstruments, listScreeners, runScreener } from "@/lib/api";
import { fmtCurrency, fmtDate, fmtNumber, fmtPct } from "@/lib/format";
import type { AssetClass, Instrument, RankMetric, ScreenerResult, ScreenerSummary, StrategyId } from "@/lib/types";
import { DEFAULT_PARAMS, STRATEGIES } from "@/lib/types";

const ASSET_CLASS_LABELS: Record<AssetClass, string> = {
  equity: "Actions",
  index: "Indices",
  forex: "Forex",
  commodity: "Matières premières",
  crypto: "Crypto",
};

const RANK_LABELS: Record<RankMetric, string> = {
  sharpe: "Sharpe",
  sortino: "Sortino",
  final_equity: "Equity finale",
  max_drawdown: "Max drawdown",
  win_rate: "Taux de réussite",
  profit_factor: "Profit factor",
  total_trades: "Nombre de trades",
};

export default function ScreenerPage() {
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [history, setHistory] = useState<ScreenerSummary[]>([]);
  const [result, setResult] = useState<ScreenerResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getInstruments().then(setInstruments).catch(() => setInstruments([]));
    listScreeners().then(setHistory).catch(() => {
      /* historique optionnel */
    });
  }, []);

  const assetClasses = useMemo(
    () => Array.from(new Set(instruments.map((i) => i.asset_class))).sort(),
    [instruments]
  );
  const [assetClass, setAssetClass] = useState<AssetClass | "">("equity");
  const [strategyId, setStrategyId] = useState<StrategyId>("sma_crossover");
  const strategy = STRATEGIES.find((s) => s.id === strategyId)!;
  const [params, setParams] = useState<Record<string, number>>(DEFAULT_PARAMS.sma_crossover);
  const [rankBy, setRankBy] = useState<RankMetric>("sharpe");
  const [engine, setEngine] = useState<"vectorized" | "event_driven">("vectorized");
  const [initialCapital, setInitialCapital] = useState(10_000);

  function handleStrategyChange(next: StrategyId) {
    setStrategyId(next);
    setParams(DEFAULT_PARAMS[next]);
  }

  const scanCount = assetClass
    ? instruments.filter((i) => i.asset_class === assetClass).length
    : instruments.length;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setIsRunning(true);
    setError(null);
    try {
      const r = await runScreener({
        asset_class: assetClass || undefined,
        strategy: strategyId,
        params,
        initial_capital: initialCapital,
        commission: 0.0005,
        slippage: 0.0005,
        engine,
        position_size: 1.0,
        rank_by: rankBy,
      });
      setResult(r);
      setHistory((h) => [
        {
          screener_run_id: r.screener_run_id,
          strategy: r.strategy,
          rank_by: r.rank_by,
          created_at: new Date().toISOString(),
          n_results: r.results.length,
        },
        ...h,
      ].slice(0, 50));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Le screener a échoué.");
    } finally {
      setIsRunning(false);
    }
  }

  function formatMetric(m: ScreenerResult["results"][number]["metrics"], key: RankMetric) {
    switch (key) {
      case "final_equity":
        return fmtCurrency(m.final_equity);
      case "max_drawdown":
        return fmtPct(m.max_drawdown);
      case "win_rate":
        return fmtPct(m.win_rate);
      case "total_trades":
        return String(m.total_trades);
      case "profit_factor":
        return m.profit_factor === null ? "∞" : fmtNumber(m.profit_factor);
      default:
        return fmtNumber(m[key]);
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <header className="mb-8">
        <h1 className="text-xl font-semibold tracking-tight">
          Probatio <span className="text-signal">/</span> screener
        </h1>
        <p className="mt-1 text-sm text-ink-muted">
          Applique une même stratégie à tout un univers d&apos;instruments et classe les résultats.
        </p>
      </header>

      {error && (
        <div className="mb-6 rounded-md border border-down/30 bg-down/10 px-4 py-3 text-sm text-down">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[360px_1fr]">
        <aside className="flex flex-col gap-6">
          <form
            onSubmit={handleSubmit}
            className="flex flex-col gap-5 rounded-lg border border-border bg-bg-panel p-5"
          >
            <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-muted">
              Configurer un scan
            </h2>

            <label className="flex flex-col gap-1.5 text-sm">
              <span className="text-xs text-ink-muted">Classe d&apos;actif (vide = tout l&apos;univers)</span>
              <select
                className="select"
                value={assetClass}
                onChange={(e) => setAssetClass(e.target.value as AssetClass | "")}
              >
                <option value="">Tout l&apos;univers disponible</option>
                {assetClasses.map((ac) => (
                  <option key={ac} value={ac}>
                    {ASSET_CLASS_LABELS[ac] ?? ac}
                  </option>
                ))}
              </select>
              <span className="text-[11px] text-ink-faint">{scanCount} instrument(s) seront scannés</span>
            </label>

            <label className="flex flex-col gap-1.5 text-sm">
              <span className="text-xs text-ink-muted">Stratégie</span>
              <select
                className="select"
                value={strategyId}
                onChange={(e) => handleStrategyChange(e.target.value as StrategyId)}
              >
                {STRATEGIES.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
              </select>
            </label>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {strategy.params.map((p) => (
                <label key={p.key} className="flex flex-col gap-1.5 text-sm">
                  <span className="text-[11px] text-ink-faint">{p.label}</span>
                  <input
                    type="number"
                    className="input"
                    min={p.min}
                    max={p.max}
                    step={p.step}
                    value={params[p.key]}
                    onChange={(e) => setParams((prev) => ({ ...prev, [p.key]: Number(e.target.value) }))}
                  />
                </label>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <label className="flex flex-col gap-1.5 text-sm">
                <span className="text-xs text-ink-muted">Classer par</span>
                <select className="select" value={rankBy} onChange={(e) => setRankBy(e.target.value as RankMetric)}>
                  {Object.entries(RANK_LABELS).map(([k, label]) => (
                    <option key={k} value={k}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1.5 text-sm">
                <span className="text-xs text-ink-muted">Moteur</span>
                <select className="select" value={engine} onChange={(e) => setEngine(e.target.value as typeof engine)}>
                  <option value="vectorized">Vectorisé</option>
                  <option value="event_driven">Event-driven</option>
                </select>
              </label>
            </div>

            <label className="flex flex-col gap-1.5 text-sm">
              <span className="text-xs text-ink-muted">Capital initial (USD)</span>
              <input
                type="number"
                className="input"
                min={100}
                step={100}
                value={initialCapital}
                onChange={(e) => setInitialCapital(Number(e.target.value))}
              />
            </label>

            <button
              type="submit"
              disabled={isRunning || scanCount === 0}
              className="mt-1 rounded-md bg-signal px-4 py-2.5 text-sm font-semibold text-bg
                         transition hover:bg-signal/90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isRunning ? "Scan en cours…" : "Lancer le screener"}
            </button>
          </form>

          <div className="rounded-lg border border-border bg-bg-panel">
            <h3 className="px-4 pt-4 text-xs font-semibold uppercase tracking-wide text-ink-muted">
              Historique
            </h3>
            {history.length === 0 ? (
              <p className="p-4 text-sm text-ink-faint">Aucun scan lancé pour l&apos;instant.</p>
            ) : (
              <ul className="max-h-[320px] overflow-y-auto p-2">
                {history.map((h) => (
                  <li key={h.screener_run_id} className="rounded-md px-3 py-2 text-sm hover:bg-bg-raised">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-ink">{h.strategy}</span>
                      <span className="text-[11px] text-ink-faint">{fmtDate(h.created_at)}</span>
                    </div>
                    <div className="mt-0.5 text-xs text-ink-muted">
                      {h.n_results ?? "—"} résultats · classé par {RANK_LABELS[h.rank_by as RankMetric] ?? h.rank_by}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </aside>

        <section className="flex flex-col gap-6">
          {result ? (
            <>
              <div className="overflow-x-auto rounded-lg border border-border bg-bg-panel">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-ink-faint">
                      <th className="px-3 py-2">#</th>
                      <th className="px-3 py-2">Symbole</th>
                      <th className="px-3 py-2">Classe</th>
                      <th className="px-3 py-2 text-right">Sharpe</th>
                      <th className="px-3 py-2 text-right">Equity finale</th>
                      <th className="px-3 py-2 text-right">Max drawdown</th>
                      <th className="px-3 py-2 text-right">Trades</th>
                      <th className="px-3 py-2 text-right">{RANK_LABELS[result.rank_by as RankMetric] ?? result.rank_by}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.results.map((r, i) => (
                      <tr key={r.symbol} className="border-b border-border/60 last:border-0">
                        <td className="px-3 py-2 tabular font-mono text-ink-faint">{i + 1}</td>
                        <td className="px-3 py-2 font-medium">{r.symbol}</td>
                        <td className="px-3 py-2 text-ink-muted">{r.asset_class}</td>
                        <td className="px-3 py-2 text-right tabular font-mono">{fmtNumber(r.metrics.sharpe)}</td>
                        <td className="px-3 py-2 text-right tabular font-mono">{fmtCurrency(r.metrics.final_equity)}</td>
                        <td className="px-3 py-2 text-right tabular font-mono text-down">
                          {fmtPct(r.metrics.max_drawdown)}
                        </td>
                        <td className="px-3 py-2 text-right tabular font-mono">{r.metrics.total_trades}</td>
                        <td className="px-3 py-2 text-right tabular font-mono text-signal">
                          {formatMetric(r.metrics, result.rank_by as RankMetric)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {result.skipped.length > 0 && (
                <div className="rounded-lg border border-border bg-bg-panel p-4 text-xs text-ink-faint">
                  <span className="font-medium text-ink-muted">{result.skipped.length} instrument(s) ignoré(s) : </span>
                  {result.skipped.map((s) => `${s.symbol} (${s.reason})`).join(" · ")}
                </div>
              )}
            </>
          ) : (
            <div className="rounded-lg border border-dashed border-border p-10 text-center text-sm text-ink-faint">
              Lance un scan pour voir le classement des instruments.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}