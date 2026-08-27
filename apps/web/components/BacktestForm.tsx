"use client";

import { useMemo, useState } from "react";
import type { AssetClass, BacktestRequest, Engine, Instrument, StrategyId } from "@/lib/types";
import { DEFAULT_PARAMS, STRATEGIES } from "@/lib/types";

const ASSET_CLASS_LABELS: Record<AssetClass, string> = {
  equity: "Actions",
  index: "Indices",
  forex: "Forex",
  commodity: "Matières premières",
  crypto: "Crypto",
};

interface Props {
  instruments: Instrument[];
  isRunning: boolean;
  onSubmit: (req: BacktestRequest) => void;
}

export default function BacktestForm({ instruments, isRunning, onSubmit }: Props) {
  const assetClasses = useMemo(
    () => Array.from(new Set(instruments.map((i) => i.asset_class))).sort(),
    [instruments]
  );

  const [assetClass, setAssetClass] = useState<AssetClass>(assetClasses[0] ?? "equity");
  const symbolsForClass = useMemo(
    () => instruments.filter((i) => i.asset_class === assetClass),
    [instruments, assetClass]
  );
  const [symbol, setSymbol] = useState<string>(symbolsForClass[0]?.symbol ?? "");

  const [strategyId, setStrategyId] = useState<StrategyId>("sma_crossover");
  const strategy = STRATEGIES.find((s) => s.id === strategyId)!;
  const [params, setParams] = useState<Record<string, number>>(DEFAULT_PARAMS.sma_crossover);

  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [initialCapital, setInitialCapital] = useState(10_000);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [commission, setCommission] = useState(0.0005);
  const [slippage, setSlippage] = useState(0.0005);
  const [engine, setEngine] = useState<Engine>("vectorized");
  const [positionSize, setPositionSize] = useState(1.0);

  function handleAssetClassChange(next: AssetClass) {
    setAssetClass(next);
    const first = instruments.find((i) => i.asset_class === next);
    setSymbol(first?.symbol ?? "");
  }

  function handleStrategyChange(next: StrategyId) {
    setStrategyId(next);
    setParams(DEFAULT_PARAMS[next]);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!symbol) return;
    onSubmit({
      symbol,
      asset_class: assetClass,
      strategy: strategyId,
      params,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      initial_capital: initialCapital,
      commission,
      slippage,
      engine,
      position_size: positionSize,
    });
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-5 rounded-lg border border-border bg-bg-panel p-5"
    >
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-muted">
          Configurer un backtest
        </h2>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Classe d'actif">
          <select
            className="select"
            value={assetClass}
            onChange={(e) => handleAssetClassChange(e.target.value as AssetClass)}
          >
            {assetClasses.map((ac) => (
              <option key={ac} value={ac}>
                {ASSET_CLASS_LABELS[ac] ?? ac}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Instrument">
          <select className="select" value={symbol} onChange={(e) => setSymbol(e.target.value)}>
            {symbolsForClass.length === 0 && <option value="">Aucun instrument disponible</option>}
            {symbolsForClass.map((i) => (
              <option key={i.symbol} value={i.symbol}>
                {i.symbol} — {i.name}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <Field label="Stratégie">
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
      </Field>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        {strategy.params.map((p) => (
          <Field key={p.key} label={p.label}>
            <input
              type="number"
              className="input"
              min={p.min}
              max={p.max}
              step={p.step}
              value={params[p.key]}
              onChange={(e) =>
                setParams((prev) => ({ ...prev, [p.key]: Number(e.target.value) }))
              }
            />
          </Field>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Depuis (optionnel)">
          <input
            type="date"
            className="input"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </Field>
        <Field label="Jusqu'à (optionnel)">
          <input
            type="date"
            className="input"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </Field>
      </div>

      <Field label="Capital initial (USD)">
        <input
          type="number"
          className="input"
          min={100}
          step={100}
          value={initialCapital}
          onChange={(e) => setInitialCapital(Number(e.target.value))}
        />
      </Field>

      <Field label="Moteur de backtest">
        <select
          className="select"
          value={engine}
          onChange={(e) => setEngine(e.target.value as Engine)}
        >
          <option value="vectorized">Vectorisé (rapide, prototypage)</option>
          <option value="event_driven">Event-driven (simulation d&apos;ordres réaliste)</option>
        </select>
      </Field>

      {engine === "event_driven" && (
        <Field label="Sizing (fraction du capital par position, ex. 1.0 = 100%)">
          <input
            type="number"
            className="input"
            min={0.01}
            max={5}
            step={0.05}
            value={positionSize}
            onChange={(e) => setPositionSize(Number(e.target.value))}
          />
        </Field>
      )}

      <button
        type="button"
        onClick={() => setShowAdvanced((v) => !v)}
        className="self-start text-xs text-ink-muted hover:text-signal"
      >
        {showAdvanced ? "− Masquer les frais avancés" : "+ Commission / slippage"}
      </button>

      {showAdvanced && (
        <div className="grid grid-cols-2 gap-4">
          <Field label="Commission (fraction, ex. 0.0005 = 5 pb)">
            <input
              type="number"
              className="input"
              min={0}
              step={0.0001}
              value={commission}
              onChange={(e) => setCommission(Number(e.target.value))}
            />
          </Field>
          <Field label="Slippage (fraction)">
            <input
              type="number"
              className="input"
              min={0}
              step={0.0001}
              value={slippage}
              onChange={(e) => setSlippage(Number(e.target.value))}
            />
          </Field>
        </div>
      )}

      <button
        type="submit"
        disabled={isRunning || !symbol}
        className="mt-1 rounded-md bg-signal px-4 py-2.5 text-sm font-semibold text-bg
                   transition hover:bg-signal/90 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isRunning ? "Calcul en cours…" : "Lancer le backtest"}
      </button>
    </form>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5 text-sm">
      <span className="text-xs text-ink-muted">{label}</span>
      {children}
    </label>
  );
}