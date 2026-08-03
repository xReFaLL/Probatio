"use client";

import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ApiError, getInstruments, runCompare } from "@/lib/api";
import { fmtCurrency, fmtDate, fmtNumber, fmtPct } from "@/lib/format";
import type { AssetClass, CompareResult, CompareVariantInput, Engine, Instrument, StrategyId } from "@/lib/types";
import { DEFAULT_PARAMS, STRATEGIES } from "@/lib/types";

const ASSET_CLASS_LABELS: Record<AssetClass, string> = {
  equity: "Actions",
  index: "Indices",
  forex: "Forex",
  commodity: "Matières premières",
  crypto: "Crypto",
};

const LINE_COLORS = ["#22d3b6", "#f5a623", "#f16565", "#60a5fa", "#c084fc", "#34d399", "#fb923c", "#f472b6"];

function newVariant(): CompareVariantInput {
  return { strategy: "sma_crossover", params: DEFAULT_PARAMS.sma_crossover, engine: "vectorized", position_size: 1.0 };
}

// Merge les courbes d'equity de chaque variante sur un calendrier commun
// (union des timestamps) pour un unique LineChart -- les variantes utilisent
// le même symbole/fenêtre temporelle donc les dates coïncident presque
// toujours, mais l'union reste plus sûre qu'un zip par index.
function mergeEquityCurves(variants: CompareResult["variants"]) {
  const byTimestamp = new Map<string, Record<string, number | string>>();
  variants.forEach((v, i) => {
    v.equity_curve.forEach((p) => {
      const row = byTimestamp.get(p.timestamp) ?? { timestamp: p.timestamp };
      row[`v${i}`] = p.equity;
      byTimestamp.set(p.timestamp, row);
    });
  });
  return Array.from(byTimestamp.values()).sort((a, b) =>
    String(a.timestamp).localeCompare(String(b.timestamp))
  );
}

export default function ComparePage() {
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [result, setResult] = useState<CompareResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getInstruments().then(setInstruments).catch(() => setInstruments([]));
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
  const [initialCapital, setInitialCapital] = useState(10_000);
  const [variants, setVariants] = useState<CompareVariantInput[]>([newVariant(), newVariant()]);

  function updateVariant(i: number, patch: Partial<CompareVariantInput>) {
    setVariants((prev) => prev.map((v, idx) => (idx === i ? { ...v, ...patch } : v)));
  }

  function updateVariantStrategy(i: number, strategy: StrategyId) {
    updateVariant(i, { strategy, params: DEFAULT_PARAMS[strategy] });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!symbol) return;
    setIsRunning(true);
    setError(null);
    try {
      const r = await runCompare({
        symbol,
        asset_class: assetClass,
        variants,
        initial_capital: initialCapital,
        commission: 0.0005,
        slippage: 0.0005,
      });
      setResult(r);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "La comparaison a échoué.");
    } finally {
      setIsRunning(false);
    }
  }

  const mergedCurve = result ? mergeEquityCurves(result.variants) : [];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <header className="mb-8">
        <h1 className="text-xl font-semibold tracking-tight">
          Probatio <span className="text-signal">/</span> comparateur
        </h1>
        <p className="mt-1 text-sm text-ink-muted">
          Lance plusieurs stratégies (ou paramétrages) sur le même instrument et compare leurs courbes
          d&apos;equity côte à côte.
        </p>
      </header>

      {error && (
        <div className="mb-6 rounded-md border border-down/30 bg-down/10 px-4 py-3 text-sm text-down">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="mb-6 flex flex-col gap-5 rounded-lg border border-border bg-bg-panel p-5">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
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
          <div className="flex items-end">
            <button
              type="button"
              disabled={variants.length >= 8}
              onClick={() => setVariants((prev) => [...prev, newVariant()])}
              className="w-full rounded-md border border-border px-3 py-2 text-sm text-ink-muted transition
                         hover:border-signal/40 hover:text-signal disabled:cursor-not-allowed disabled:opacity-40"
            >
              + Ajouter une variante
            </button>
          </div>
        </div>

        <div className="flex flex-col gap-3">
          {variants.map((v, i) => {
            const spec = STRATEGIES.find((s) => s.id === v.strategy)!;
            return (
              <div key={i} className="grid grid-cols-2 items-end gap-3 rounded-md border border-border/60 p-3 sm:grid-cols-6">
                <span
                  className="col-span-2 text-xs font-medium sm:col-span-1"
                  style={{ color: LINE_COLORS[i % LINE_COLORS.length] }}
                >
                  Variante {i + 1}
                </span>
                <label className="flex flex-col gap-1 text-sm">
                  <span className="text-[11px] text-ink-faint">Stratégie</span>
                  <select
                    className="select"
                    value={v.strategy}
                    onChange={(e) => updateVariantStrategy(i, e.target.value as StrategyId)}
                  >
                    {STRATEGIES.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                </label>
                {spec.params.map((p) => (
                  <label key={p.key} className="flex flex-col gap-1 text-sm">
                    <span className="text-[11px] text-ink-faint">{p.label}</span>
                    <input
                      type="number"
                      className="input"
                      min={p.min}
                      max={p.max}
                      step={p.step}
                      value={v.params[p.key] ?? 0}
                      onChange={(e) =>
                        updateVariant(i, { params: { ...v.params, [p.key]: Number(e.target.value) } })
                      }
                    />
                  </label>
                ))}
                <label className="flex flex-col gap-1 text-sm">
                  <span className="text-[11px] text-ink-faint">Moteur</span>
                  <select
                    className="select"
                    value={v.engine}
                    onChange={(e) => updateVariant(i, { engine: e.target.value as Engine })}
                  >
                    <option value="vectorized">Vectorisé</option>
                    <option value="event_driven">Event-driven</option>
                  </select>
                </label>
                {variants.length > 1 && (
                  <button
                    type="button"
                    onClick={() => setVariants((prev) => prev.filter((_, idx) => idx !== i))}
                    className="self-center text-xs text-ink-faint hover:text-down"
                  >
                    Retirer
                  </button>
                )}
              </div>
            );
          })}
        </div>

        <button
          type="submit"
          disabled={isRunning || !symbol}
          className="self-start rounded-md bg-signal px-4 py-2.5 text-sm font-semibold text-bg
                     transition hover:bg-signal/90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isRunning ? "Calcul en cours…" : "Comparer"}
        </button>
      </form>

      {result && (
        <div className="flex flex-col gap-6">
          <div className="rounded-lg border border-border bg-bg-panel p-4">
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-ink-muted">
              Courbes d&apos;equity superposées
            </h3>
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={mergedCurve} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="#161d28" vertical={false} />
                <XAxis
                  dataKey="timestamp"
                  tickFormatter={(v) => fmtDate(String(v))}
                  tick={{ fill: "#5b6472", fontSize: 11 }}
                  minTickGap={40}
                  axisLine={{ stroke: "#1f2937" }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "#5b6472", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  width={70}
                  tickFormatter={(v) => fmtCurrency(Number(v))}
                />
                <Tooltip
                  contentStyle={{ background: "#111720", border: "1px solid #1f2937", borderRadius: 8, fontSize: 12 }}
                  labelFormatter={(v) => fmtDate(String(v))}
                  formatter={(value: number, key: string) => {
                    const idx = Number(key.replace("v", ""));
                    return [fmtCurrency(value), result.variants[idx]?.label ?? key];
                  }}
                />
                <Legend
                  formatter={(key: string) => {
                    const idx = Number(String(key).replace("v", ""));
                    return result.variants[idx]?.label ?? key;
                  }}
                />
                {result.variants.map((v, i) => (
                  <Line
                    key={i}
                    type="monotone"
                    dataKey={`v${i}`}
                    stroke={LINE_COLORS[i % LINE_COLORS.length]}
                    strokeWidth={1.5}
                    dot={false}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="overflow-x-auto rounded-lg border border-border bg-bg-panel">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-ink-faint">
                  <th className="px-3 py-2">Variante</th>
                  <th className="px-3 py-2">Moteur</th>
                  <th className="px-3 py-2 text-right">Equity finale</th>
                  <th className="px-3 py-2 text-right">Sharpe</th>
                  <th className="px-3 py-2 text-right">Sortino</th>
                  <th className="px-3 py-2 text-right">Max drawdown</th>
                  <th className="px-3 py-2 text-right">Taux de réussite</th>
                  <th className="px-3 py-2 text-right">Trades</th>
                </tr>
              </thead>
              <tbody>
                {result.variants.map((v, i) => (
                  <tr key={i} className="border-b border-border/60 last:border-0">
                    <td className="px-3 py-2 font-medium" style={{ color: LINE_COLORS[i % LINE_COLORS.length] }}>
                      {v.label}
                    </td>
                    <td className="px-3 py-2 text-ink-muted">{v.engine}</td>
                    <td className="px-3 py-2 text-right tabular font-mono">{fmtCurrency(v.metrics.final_equity)}</td>
                    <td className="px-3 py-2 text-right tabular font-mono">{fmtNumber(v.metrics.sharpe)}</td>
                    <td className="px-3 py-2 text-right tabular font-mono">{fmtNumber(v.metrics.sortino)}</td>
                    <td className="px-3 py-2 text-right tabular font-mono text-down">
                      {fmtPct(v.metrics.max_drawdown)}
                    </td>
                    <td className="px-3 py-2 text-right tabular font-mono">{fmtPct(v.metrics.win_rate)}</td>
                    <td className="px-3 py-2 text-right tabular font-mono">{v.metrics.total_trades}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}