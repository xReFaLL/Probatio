"use client";

import { useEffect, useMemo, useState } from "react";
import EquityChart from "@/components/EquityChart";
import MetricsPanel from "@/components/MetricsPanel";
import { ApiError, getInstruments, listWalkForwards, runWalkForward } from "@/lib/api";
import { fmtDate, fmtNumber, fmtPct } from "@/lib/format";
import type {
  AssetClass,
  Instrument,
  StrategyId,
  WalkForwardResult,
  WalkForwardSummary,
} from "@/lib/types";
import { DEFAULT_PARAMS, STRATEGIES } from "@/lib/types";

const ASSET_CLASS_LABELS: Record<AssetClass, string> = {
  equity: "Actions",
  index: "Indices",
  forex: "Forex",
  commodity: "Matières premières",
  crypto: "Crypto",
};

// Grille de paramètres saisie en texte ("10,20,30") -> nombre[] ; une valeur
// seule ("20") reste une grille à un point, comme accepté côté API
// (walk_forward._param_grid traite un scalaire comme liste à un élément).
function parseGrid(raw: string): number[] {
  return raw
    .split(",")
    .map((v) => Number(v.trim()))
    .filter((v) => !Number.isNaN(v));
}

export default function WalkForwardPage() {
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [history, setHistory] = useState<WalkForwardSummary[]>([]);
  const [result, setResult] = useState<WalkForwardResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getInstruments().then(setInstruments).catch(() => setInstruments([]));
    listWalkForwards().then(setHistory).catch(() => {
      /* historique optionnel */
    });
  }, []);

  const assetClasses = useMemo(
    () => Array.from(new Set(instruments.map((i) => i.asset_class))).sort(),
    [instruments]
  );
  const [assetClass, setAssetClass] = useState<AssetClass>("equity");
  const symbolsForClass = useMemo(
    () => instruments.filter((i) => i.asset_class === assetClass),
    [instruments, assetClass]
  );
  const [symbol, setSymbol] = useState("");

  const [strategyId, setStrategyId] = useState<StrategyId>("sma_crossover");
  const strategy = STRATEGIES.find((s) => s.id === strategyId)!;
  const [gridText, setGridText] = useState<Record<string, string>>(
    Object.fromEntries(Object.entries(DEFAULT_PARAMS.sma_crossover).map(([k, v]) => [k, String(v)]))
  );

  const [inSampleBars, setInSampleBars] = useState(504);
  const [outSampleBars, setOutSampleBars] = useState(126);
  const [optimizeMetric, setOptimizeMetric] = useState<
    "sharpe" | "sortino" | "profit_factor" | "final_equity"
  >("sharpe");
  const [initialCapital, setInitialCapital] = useState(10_000);
  const [engine, setEngine] = useState<"vectorized" | "event_driven">("vectorized");

  function handleStrategyChange(next: StrategyId) {
    setStrategyId(next);
    setGridText(Object.fromEntries(Object.entries(DEFAULT_PARAMS[next]).map(([k, v]) => [k, String(v)])));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!symbol) return;
    setIsRunning(true);
    setError(null);
    try {
      const param_grid = Object.fromEntries(
        strategy.params.map((p) => [p.key, parseGrid(gridText[p.key] ?? "")])
      );
      const r = await runWalkForward({
        symbol,
        asset_class: assetClass,
        strategy: strategyId,
        param_grid,
        in_sample_bars: inSampleBars,
        out_sample_bars: outSampleBars,
        optimize_metric: optimizeMetric,
        initial_capital: initialCapital,
        commission: 0.0005,
        slippage: 0.0005,
        engine,
        position_size: 1.0,
      });
      setResult(r);
      setHistory((h) => [
        {
          walk_forward_run_id: r.walk_forward_run_id,
          symbol: r.symbol,
          strategy: r.strategy,
          created_at: new Date().toISOString(),
          n_windows: r.n_windows,
          aggregate_sharpe: r.aggregate_metrics.sharpe,
        },
        ...h,
      ].slice(0, 50));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Le walk-forward a échoué.");
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <header className="mb-8">
        <h1 className="text-xl font-semibold tracking-tight">
          Probatio <span className="text-signal">/</span> walk-forward
        </h1>
        <p className="mt-1 text-sm text-ink-muted">
          Optimise les paramètres sur une fenêtre glissante in-sample, valide sur la fenêtre
          out-of-sample suivante — jamais vue pendant l&apos;optimisation.
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
              Configurer un walk-forward
            </h2>

            <div className="grid grid-cols-2 gap-4">
              <label className="flex flex-col gap-1.5 text-sm">
                <span className="text-xs text-ink-muted">Classe d&apos;actif</span>
                <select
                  className="select"
                  value={assetClass}
                  onChange={(e) => {
                    const next = e.target.value as AssetClass;
                    setAssetClass(next);
                    setSymbol(instruments.find((i) => i.asset_class === next)?.symbol ?? "");
                  }}
                >
                  {(assetClasses.length ? assetClasses : (["equity"] as AssetClass[])).map((ac) => (
                    <option key={ac} value={ac}>
                      {ASSET_CLASS_LABELS[ac] ?? ac}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1.5 text-sm">
                <span className="text-xs text-ink-muted">Instrument</span>
                <select className="select" value={symbol} onChange={(e) => setSymbol(e.target.value)}>
                  {symbolsForClass.length === 0 && <option value="">Aucun</option>}
                  {symbolsForClass.map((i) => (
                    <option key={i.symbol} value={i.symbol}>
                      {i.symbol}
                    </option>
                  ))}
                </select>
              </label>
            </div>

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

            <div className="flex flex-col gap-3">
              <span className="text-xs text-ink-muted">
                Grille de paramètres (valeurs séparées par des virgules)
              </span>
              <div className="grid grid-cols-2 gap-3">
                {strategy.params.map((p) => (
                  <label key={p.key} className="flex flex-col gap-1.5 text-sm">
                    <span className="text-[11px] text-ink-faint">{p.label}</span>
                    <input
                      type="text"
                      className="input"
                      placeholder={`${p.min},${p.max}`}
                      value={gridText[p.key] ?? ""}
                      onChange={(e) => setGridText((prev) => ({ ...prev, [p.key]: e.target.value }))}
                    />
                  </label>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <label className="flex flex-col gap-1.5 text-sm">
                <span className="text-xs text-ink-muted">Barres in-sample</span>
                <input
                  type="number"
                  className="input"
                  min={20}
                  value={inSampleBars}
                  onChange={(e) => setInSampleBars(Number(e.target.value))}
                />
              </label>
              <label className="flex flex-col gap-1.5 text-sm">
                <span className="text-xs text-ink-muted">Barres out-of-sample</span>
                <input
                  type="number"
                  className="input"
                  min={5}
                  value={outSampleBars}
                  onChange={(e) => setOutSampleBars(Number(e.target.value))}
                />
              </label>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <label className="flex flex-col gap-1.5 text-sm">
                <span className="text-xs text-ink-muted">Métrique d&apos;optimisation</span>
                <select
                  className="select"
                  value={optimizeMetric}
                  onChange={(e) => setOptimizeMetric(e.target.value as typeof optimizeMetric)}
                >
                  <option value="sharpe">Sharpe</option>
                  <option value="sortino">Sortino</option>
                  <option value="profit_factor">Profit factor</option>
                  <option value="final_equity">Equity finale</option>
                </select>
              </label>
              <label className="flex flex-col gap-1.5 text-sm">
                <span className="text-xs text-ink-muted">Moteur</span>
                <select
                  className="select"
                  value={engine}
                  onChange={(e) => setEngine(e.target.value as typeof engine)}
                >
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
              disabled={isRunning || !symbol}
              className="mt-1 rounded-md bg-signal px-4 py-2.5 text-sm font-semibold text-bg
                         transition hover:bg-signal/90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isRunning ? "Calcul en cours…" : "Lancer le walk-forward"}
            </button>
          </form>

          <div className="rounded-lg border border-border bg-bg-panel">
            <h3 className="px-4 pt-4 text-xs font-semibold uppercase tracking-wide text-ink-muted">
              Historique
            </h3>
            {history.length === 0 ? (
              <p className="p-4 text-sm text-ink-faint">Aucun walk-forward lancé pour l&apos;instant.</p>
            ) : (
              <ul className="max-h-[320px] overflow-y-auto p-2">
                {history.map((h) => (
                  <li key={h.walk_forward_run_id} className="rounded-md px-3 py-2 text-sm hover:bg-bg-raised">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-ink">{h.symbol}</span>
                      <span className="text-[11px] text-ink-faint">{fmtDate(h.created_at)}</span>
                    </div>
                    <div className="mt-0.5 flex items-center justify-between text-xs text-ink-muted">
                      <span>{h.strategy}</span>
                      <span className="tabular font-mono">
                        {h.n_windows ?? "—"} fenêtres
                        {h.aggregate_sharpe != null ? ` · Sharpe ${fmtNumber(h.aggregate_sharpe, 2)}` : ""}
                      </span>
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
              <MetricsPanel metrics={result.aggregate_metrics} />
              <EquityChart
                equityCurve={result.stitched_equity_curve}
                initialCapital={result.stitched_equity_curve[0]?.equity ?? 10_000}
              />

              <div className="overflow-x-auto rounded-lg border border-border bg-bg-panel">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-ink-faint">
                      <th className="px-3 py-2">Fenêtre</th>
                      <th className="px-3 py-2">In-sample</th>
                      <th className="px-3 py-2">Out-of-sample</th>
                      <th className="px-3 py-2">Meilleurs paramètres</th>
                      <th className="px-3 py-2 text-right">Sharpe OOS</th>
                      <th className="px-3 py-2 text-right">Drawdown OOS</th>
                      <th className="px-3 py-2 text-right">Trades</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.windows.map((w) => (
                      <tr key={w.window_index} className="border-b border-border/60 last:border-0">
                        <td className="px-3 py-2 tabular font-mono text-ink-faint">{w.window_index + 1}</td>
                        <td className="px-3 py-2 text-xs text-ink-muted">
                          {fmtDate(w.is_start)} → {fmtDate(w.is_end)}
                        </td>
                        <td className="px-3 py-2 text-xs text-ink-muted">
                          {fmtDate(w.oos_start)} → {fmtDate(w.oos_end)}
                        </td>
                        <td className="px-3 py-2 text-xs">
                          {Object.entries(w.best_params).map(([k, v]) => `${k}=${v}`).join(", ")}
                        </td>
                        <td className="px-3 py-2 text-right tabular font-mono">
                          {fmtNumber(w.oos_metrics.sharpe)}
                        </td>
                        <td className="px-3 py-2 text-right tabular font-mono text-down">
                          {fmtPct(w.oos_metrics.max_drawdown)}
                        </td>
                        <td className="px-3 py-2 text-right tabular font-mono">
                          {w.oos_metrics.total_trades}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div className="rounded-lg border border-dashed border-border p-10 text-center text-sm text-ink-faint">
              Configure et lance un walk-forward pour voir les fenêtres in-sample/out-of-sample et la
              courbe d&apos;equity recollée.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}