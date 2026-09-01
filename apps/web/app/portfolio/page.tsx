"use client";

import { useEffect, useMemo, useState } from "react";
import EquityChart from "@/components/EquityChart";
import MetricsPanel from "@/components/MetricsPanel";
import { ApiError, getInstruments, listPortfolios, runPortfolio } from "@/lib/api";
import { fmtCurrency, fmtDate, fmtNumber, fmtPct } from "@/lib/format";
import type {
  AssetClass,
  Engine,
  Instrument,
  PortfolioLegInput,
  PortfolioResult,
  PortfolioSummary,
  StrategyId,
} from "@/lib/types";
import { DEFAULT_PARAMS, STRATEGIES } from "@/lib/types";

const ASSET_CLASS_LABELS: Record<AssetClass, string> = {
  equity: "Actions",
  index: "Indices",
  forex: "Forex",
  commodity: "Matières premières",
  crypto: "Crypto",
};

function newLeg(defaultSymbol: string, defaultAssetClass: AssetClass): PortfolioLegInput {
  return {
    symbol: defaultSymbol,
    asset_class: defaultAssetClass,
    strategy: "sma_crossover",
    params: DEFAULT_PARAMS.sma_crossover,
    weight: 1,
  };
}

export default function PortfolioPage() {
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [history, setHistory] = useState<PortfolioSummary[]>([]);
  const [result, setResult] = useState<PortfolioResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getInstruments().then(setInstruments).catch(() => setInstruments([]));
    listPortfolios().then(setHistory).catch(() => {
      /* historique optionnel */
    });
  }, []);

  const [name, setName] = useState("Mon portefeuille");
  const [legs, setLegs] = useState<PortfolioLegInput[]>([]);
  const [rebalance, setRebalance] = useState<"none" | "monthly" | "quarterly">("none");
  const [initialCapital, setInitialCapital] = useState(10_000);
  const [engine, setEngine] = useState<Engine>("vectorized");

  useEffect(() => {
    if (instruments.length && legs.length === 0) {
      setLegs([
        newLeg(instruments[0].symbol, instruments[0].asset_class),
        ...(instruments[1] ? [newLeg(instruments[1].symbol, instruments[1].asset_class)] : []),
      ]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [instruments]);

  const totalWeight = legs.reduce((acc, l) => acc + (l.weight || 0), 0);

  function updateLeg(i: number, patch: Partial<PortfolioLegInput>) {
    setLegs((prev) => prev.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));
  }

  function updateLegStrategy(i: number, strategy: StrategyId) {
    updateLeg(i, { strategy, params: DEFAULT_PARAMS[strategy] });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (legs.length === 0) return;
    setIsRunning(true);
    setError(null);
    try {
      const r = await runPortfolio({
        name,
        legs,
        initial_capital: initialCapital,
        commission: 0.0005,
        slippage: 0.0005,
        engine,
        position_size: 1.0,
        rebalance,
      });
      setResult(r);
      setHistory((h) => [
        {
          portfolio_run_id: r.portfolio_run_id,
          name: r.name,
          created_at: new Date().toISOString(),
          final_equity: r.equity_curve[r.equity_curve.length - 1]?.equity ?? null,
          n_legs: r.legs.length,
        },
        ...h,
      ].slice(0, 50));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Le backtest de portefeuille a échoué.");
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <header className="mb-8">
        <h1 className="text-xl font-semibold tracking-tight">
          Probatio <span className="text-signal">/</span> portefeuille
        </h1>
        <p className="mt-1 text-sm text-ink-muted">
          Combine plusieurs jambes (instrument + stratégie + poids) en une seule courbe d&apos;equity
          pondérée, avec ou sans rebalancement périodique.
        </p>
      </header>

      {error && (
        <div className="mb-6 rounded-md border border-down/30 bg-down/10 px-4 py-3 text-sm text-down">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[420px_1fr]">
        <aside className="flex flex-col gap-6">
          <form
            onSubmit={handleSubmit}
            className="flex flex-col gap-5 rounded-lg border border-border bg-bg-panel p-5"
          >
            <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-muted">
              Configurer le portefeuille
            </h2>

            <label className="flex flex-col gap-1.5 text-sm">
              <span className="text-xs text-ink-muted">Nom</span>
              <input type="text" className="input" value={name} onChange={(e) => setName(e.target.value)} />
            </label>

            <div className="flex flex-col gap-3">
              {legs.map((leg, i) => {
                const spec = STRATEGIES.find((s) => s.id === leg.strategy)!;
                const symbolsForClass = instruments.filter((ins) => ins.asset_class === leg.asset_class);
                return (
                  <div key={i} className="flex flex-col gap-2 rounded-md border border-border/60 p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-ink-muted">Jambe {i + 1}</span>
                      {legs.length > 1 && (
                        <button
                          type="button"
                          onClick={() => setLegs((prev) => prev.filter((_, idx) => idx !== i))}
                          className="text-xs text-ink-faint hover:text-down"
                        >
                          Retirer
                        </button>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <select
                        className="select"
                        value={leg.asset_class}
                        onChange={(e) => {
                          const ac = e.target.value as AssetClass;
                          const first = instruments.find((ins) => ins.asset_class === ac);
                          updateLeg(i, { asset_class: ac, symbol: first?.symbol ?? "" });
                        }}
                      >
                        {Array.from(new Set(instruments.map((ins) => ins.asset_class))).map((ac) => (
                          <option key={ac} value={ac}>
                            {ASSET_CLASS_LABELS[ac] ?? ac}
                          </option>
                        ))}
                      </select>
                      <select
                        className="select"
                        value={leg.symbol}
                        onChange={(e) => updateLeg(i, { symbol: e.target.value })}
                      >
                        {symbolsForClass.map((ins) => (
                          <option key={ins.symbol} value={ins.symbol}>
                            {ins.symbol}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <select
                        className="select"
                        value={leg.strategy}
                        onChange={(e) => updateLegStrategy(i, e.target.value as StrategyId)}
                      >
                        {STRATEGIES.map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.label}
                          </option>
                        ))}
                      </select>
                      <label className="flex items-center gap-2 text-sm">
                        <span className="text-xs text-ink-faint">Poids</span>
                        <input
                          type="number"
                          className="input"
                          min={0.01}
                          step={0.1}
                          value={leg.weight}
                          onChange={(e) => updateLeg(i, { weight: Number(e.target.value) })}
                        />
                      </label>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      {spec.params.map((p) => (
                        <label key={p.key} className="flex flex-col gap-1 text-xs">
                          <span className="text-ink-faint">{p.label}</span>
                          <input
                            type="number"
                            className="input"
                            min={p.min}
                            max={p.max}
                            step={p.step}
                            value={leg.params[p.key] ?? 0}
                            onChange={(e) =>
                              updateLeg(i, { params: { ...leg.params, [p.key]: Number(e.target.value) } })
                            }
                          />
                        </label>
                      ))}
                    </div>
                  </div>
                );
              })}

              <button
                type="button"
                onClick={() =>
                  setLegs((prev) => [
                    ...prev,
                    newLeg(instruments[0]?.symbol ?? "", instruments[0]?.asset_class ?? "equity"),
                  ])
                }
                className="rounded-md border border-dashed border-border px-3 py-2 text-xs text-ink-muted
                           transition hover:border-signal/40 hover:text-signal"
              >
                + Ajouter une jambe
              </button>

              <p className="text-[11px] text-ink-faint">
                Poids total : {fmtNumber(totalWeight, 2)} (normalisé automatiquement à 100% côté moteur)
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <label className="flex flex-col gap-1.5 text-sm">
                <span className="text-xs text-ink-muted">Rebalancement</span>
                <select
                  className="select"
                  value={rebalance}
                  onChange={(e) => setRebalance(e.target.value as typeof rebalance)}
                >
                  <option value="none">Aucun (buy & hold)</option>
                  <option value="monthly">Mensuel</option>
                  <option value="quarterly">Trimestriel</option>
                </select>
              </label>
              <label className="flex flex-col gap-1.5 text-sm">
                <span className="text-xs text-ink-muted">Moteur</span>
                <select className="select" value={engine} onChange={(e) => setEngine(e.target.value as Engine)}>
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
              disabled={isRunning || legs.length === 0}
              className="mt-1 rounded-md bg-signal px-4 py-2.5 text-sm font-semibold text-bg
                         transition hover:bg-signal/90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isRunning ? "Calcul en cours…" : "Lancer le backtest de portefeuille"}
            </button>
          </form>

          <div className="rounded-lg border border-border bg-bg-panel">
            <h3 className="px-4 pt-4 text-xs font-semibold uppercase tracking-wide text-ink-muted">
              Historique
            </h3>
            {history.length === 0 ? (
              <p className="p-4 text-sm text-ink-faint">Aucun portefeuille lancé pour l&apos;instant.</p>
            ) : (
              <ul className="max-h-[280px] overflow-y-auto p-2">
                {history.map((h) => (
                  <li key={h.portfolio_run_id} className="rounded-md px-3 py-2 text-sm hover:bg-bg-raised">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-ink">{h.name ?? `Portefeuille #${h.portfolio_run_id}`}</span>
                      <span className="text-[11px] text-ink-faint">{fmtDate(h.created_at)}</span>
                    </div>
                    <div className="mt-0.5 flex items-center justify-between text-xs text-ink-muted">
                      <span>{h.n_legs ?? "—"} jambe(s)</span>
                      <span className="tabular font-mono">
                        {h.final_equity != null ? fmtCurrency(h.final_equity) : "—"}
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
                equityCurve={result.equity_curve}
                initialCapital={result.equity_curve[0]?.equity ?? initialCapital}
              />

              <div className="overflow-x-auto rounded-lg border border-border bg-bg-panel">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-ink-faint">
                      <th className="px-3 py-2">Jambe</th>
                      <th className="px-3 py-2">Stratégie</th>
                      <th className="px-3 py-2 text-right">Poids</th>
                      <th className="px-3 py-2 text-right">Sharpe (isolé)</th>
                      <th className="px-3 py-2 text-right">Equity finale (isolée)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.legs.map((leg, i) => (
                      <tr key={i} className="border-b border-border/60 last:border-0">
                        <td className="px-3 py-2 font-medium">{leg.symbol}</td>
                        <td className="px-3 py-2 text-ink-muted">{leg.strategy}</td>
                        <td className="px-3 py-2 text-right tabular font-mono">{fmtPct(leg.weight)}</td>
                        <td className="px-3 py-2 text-right tabular font-mono">{fmtNumber(leg.metrics.sharpe)}</td>
                        <td className="px-3 py-2 text-right tabular font-mono">
                          {fmtCurrency(leg.metrics.final_equity)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="border-t border-border px-3 py-2 text-[11px] text-ink-faint">
                  Sharpe/equity « isolés » = performance de chaque jambe backtestée seule, avant
                  recombinaison pondérée — la courbe et les métriques ci-dessus reflètent le portefeuille
                  combiné.
                </p>
              </div>
            </>
          ) : (
            <div className="rounded-lg border border-dashed border-border p-10 text-center text-sm text-ink-faint">
              Configure au moins une jambe et lance le backtest pour voir la courbe combinée.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}