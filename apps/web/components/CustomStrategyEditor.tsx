"use client";

import { useEffect, useMemo, useState } from "react";
import CodeEditor from "@/components/CodeEditor";
import EquityChart from "@/components/EquityChart";
import MetricsPanel from "@/components/MetricsPanel";
import {
  addCustomStrategyVersion,
  ApiError,
  backtestCustomStrategy,
  createCustomStrategy,
  getInstruments,
  listCustomStrategies,
  listCustomStrategyLogs,
  testCustomStrategy,
} from "@/lib/api";
import type {
  AssetClass,
  BacktestResult,
  CustomStrategyMode,
  CustomStrategySummary,
  CustomStrategyTestResult,
  Engine,
  ExecutionLog,
  Instrument,
} from "@/lib/types";
import { CUSTOM_STRATEGY_TEMPLATES } from "@/lib/types";

const ASSET_CLASS_LABELS: Record<AssetClass, string> = {
  equity: "Actions",
  index: "Indices",
  forex: "Forex",
  commodity: "Matières premières",
  crypto: "Crypto",
};

const STATUS_LABELS: Record<CustomStrategyTestResult["status"], string> = {
  ok: "OK",
  invalid: "Code invalide",
  error: "Erreur d'exécution",
  timeout: "Temps limite dépassé",
};

export default function CustomStrategyEditor() {
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [strategies, setStrategies] = useState<CustomStrategySummary[]>([]);

  useEffect(() => {
    getInstruments().then(setInstruments).catch(() => setInstruments([]));
    listCustomStrategies().then(setStrategies).catch(() => setStrategies([]));
  }, []);

  const [mode, setMode] = useState<CustomStrategyMode>("vectorized");
  const [code, setCode] = useState(CUSTOM_STRATEGY_TEMPLATES.vectorized);
  const [name, setName] = useState("Ma stratégie");
  const [description, setDescription] = useState("");
  const [savedStrategyId, setSavedStrategyId] = useState<number | null>(null);

  const [assetClass, setAssetClass] = useState<AssetClass>("equity");
  const symbolsForClass = useMemo(
    () => instruments.filter((i) => i.asset_class === assetClass),
    [instruments, assetClass]
  );
  const [symbol, setSymbol] = useState("");
  useEffect(() => {
    if (!symbol && symbolsForClass.length) setSymbol(symbolsForClass[0].symbol);
  }, [symbolsForClass, symbol]);

  const [paramsText, setParamsText] = useState('{\n  "fast": 20,\n  "slow": 50\n}');
  const paramsError = useMemo(() => {
    try {
      JSON.parse(paramsText);
      return null;
    } catch {
      return "JSON invalide";
    }
  }, [paramsText]);

  const [engine, setEngine] = useState<Engine>("vectorized");
  const [initialCapital, setInitialCapital] = useState(10_000);

  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<CustomStrategyTestResult | null>(null);

  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const [isBacktesting, setIsBacktesting] = useState(false);
  const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(null);
  const [backtestError, setBacktestError] = useState<string | null>(null);

  const [logs, setLogs] = useState<ExecutionLog[]>([]);

  function handleModeChange(next: CustomStrategyMode) {
    setMode(next);
    // Ne remplace le code que si l'utilisateur n'a pas encore commencé à
    // écrire quelque chose de différent du squelette -- évite d'effacer du
    // travail en cours par un simple changement de mode par erreur.
    if (code === CUSTOM_STRATEGY_TEMPLATES.vectorized || code === CUSTOM_STRATEGY_TEMPLATES.event_driven) {
      setCode(CUSTOM_STRATEGY_TEMPLATES[next]);
    }
  }

  async function handleQuickTest() {
    if (!symbol || paramsError) return;
    setIsTesting(true);
    setTestResult(null);
    try {
      const params = JSON.parse(paramsText);
      const res = await testCustomStrategy({ code, mode, params, symbol, asset_class: assetClass });
      setTestResult(res);
    } catch (e) {
      setTestResult({
        status: "error",
        positions: [],
        timestamps: [],
        errors: [],
        error: e instanceof ApiError ? e.message : "Erreur réseau lors du test",
        stdout: "",
        stderr: "",
        execution_time_ms: 0,
      });
    } finally {
      setIsTesting(false);
    }
  }

  async function handleSave() {
    setIsSaving(true);
    setSaveError(null);
    try {
      if (savedStrategyId === null) {
        const created = await createCustomStrategy({ name, description, code, mode });
        setSavedStrategyId(created.strategy_id);
      } else {
        await addCustomStrategyVersion(savedStrategyId, { code, mode });
      }
      const updated = await listCustomStrategies();
      setStrategies(updated);
      if (savedStrategyId !== null) {
        listCustomStrategyLogs(savedStrategyId).then(setLogs).catch(() => {});
      }
    } catch (e) {
      setSaveError(e instanceof ApiError ? e.message : "Erreur lors de la sauvegarde");
    } finally {
      setIsSaving(false);
    }
  }

  function loadStrategy(s: CustomStrategySummary) {
    setSavedStrategyId(s.strategy_id);
    setName(s.name);
    setDescription(s.description ?? "");
    setMode(s.latest_mode);
    // Le code de la version n'est pas dans le résumé -- on va le chercher
    // via l'endpoint détail (léger, pas besoin d'un state dédié ici).
    import("@/lib/api").then(({ getCustomStrategy }) =>
      getCustomStrategy(s.strategy_id).then(() => {
        // Le contrat API ne renvoie pas le code brut dans CustomStrategyOut
        // (uniquement les métadonnées de version) -- on part du template du
        // mode courant pour l'édition ; charger le code exact nécessiterait
        // un endpoint GET /custom-strategies/{id}/versions/{version}/code
        // dédié, non prévu dans ce sprint (voir résumé de sprint : limitation connue).
        setCode(CUSTOM_STRATEGY_TEMPLATES[s.latest_mode]);
      })
    );
    listCustomStrategyLogs(s.strategy_id).then(setLogs).catch(() => {});
  }

  async function handleBacktest() {
    if (savedStrategyId === null || !symbol || paramsError) return;
    setIsBacktesting(true);
    setBacktestError(null);
    setBacktestResult(null);
    try {
      const params = JSON.parse(paramsText);
      const res = await backtestCustomStrategy(savedStrategyId, {
        symbol,
        asset_class: assetClass,
        params,
        initial_capital: initialCapital,
        commission: 0.0005,
        slippage: 0.0005,
        engine,
        position_size: 1.0,
      });
      setBacktestResult(res);
      listCustomStrategyLogs(savedStrategyId).then(setLogs).catch(() => {});
    } catch (e) {
      setBacktestError(e instanceof ApiError ? e.message : "Erreur lors du backtest");
    } finally {
      setIsBacktesting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        {/* --- Éditeur ------------------------------------------------- */}
        <div className="flex flex-col gap-4 rounded-lg border border-border bg-bg-panel p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-muted">
              Code de la stratégie
            </h2>
            <div className="flex gap-2">
              {(["vectorized", "event_driven"] as CustomStrategyMode[]).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => handleModeChange(m)}
                  className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                    mode === m
                      ? "bg-signal/15 text-signal ring-1 ring-signal/40"
                      : "text-ink-muted hover:bg-bg-raised"
                  }`}
                >
                  {m === "vectorized" ? "Vectorisé (generate_signals)" : "Event-driven (on_bar)"}
                </button>
              ))}
            </div>
          </div>

          <CodeEditor value={code} onChange={setCode} />

          <div className="grid grid-cols-2 gap-4">
            <Field label="Nom de la stratégie">
              <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
            </Field>
            <Field label="Description (optionnel)">
              <input
                className="input"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </Field>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={handleQuickTest}
              disabled={isTesting || !symbol || !!paramsError}
              className="rounded-md border border-border px-4 py-2 text-sm font-medium text-ink
                         transition hover:bg-bg-raised disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isTesting ? "Test en cours…" : "Tester (échantillon réduit)"}
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving}
              className="rounded-md bg-signal px-4 py-2 text-sm font-semibold text-bg
                         transition hover:bg-signal/90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSaving ? "Sauvegarde…" : savedStrategyId === null ? "Sauvegarder" : "Sauvegarder une nouvelle version"}
            </button>
            {saveError && <span className="text-xs text-down">{saveError}</span>}
            {savedStrategyId !== null && (
              <span className="text-xs text-ink-faint">strategy_id={savedStrategyId}</span>
            )}
          </div>

          {testResult && (
            <div
              className={`rounded-md border p-3 text-xs ${
                testResult.status === "ok"
                  ? "border-up/30 bg-up/5 text-ink"
                  : "border-down/30 bg-down/5 text-ink"
              }`}
            >
              <div className="mb-1 font-semibold">
                {STATUS_LABELS[testResult.status]} — {testResult.execution_time_ms} ms
              </div>
              {testResult.status === "ok" && (
                <div className="text-ink-muted">
                  {testResult.positions.length} barres testées · dernière position :{" "}
                  {testResult.positions.at(-1)}
                </div>
              )}
              {testResult.errors.length > 0 && (
                <ul className="mt-1 list-disc pl-4 text-down">
                  {testResult.errors.map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
              )}
              {testResult.error && <div className="mt-1 text-down">{testResult.error}</div>}
              {testResult.stderr && (
                <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-ink-faint">
                  {testResult.stderr}
                </pre>
              )}
            </div>
          )}
        </div>

        {/* --- Paramètres d'exécution ------------------------------------ */}
        <div className="flex flex-col gap-4 rounded-lg border border-border bg-bg-panel p-5">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-muted">
            Exécution
          </h2>

          <Field label="Classe d'actif">
            <select
              className="select"
              value={assetClass}
              onChange={(e) => {
                setAssetClass(e.target.value as AssetClass);
                setSymbol("");
              }}
            >
              {Object.entries(ASSET_CLASS_LABELS).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
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

          <Field label="Paramètres (JSON, passés à params)">
            <textarea
              className="input min-h-[100px] font-mono text-xs"
              value={paramsText}
              onChange={(e) => setParamsText(e.target.value)}
            />
            {paramsError && <span className="text-xs text-down">{paramsError}</span>}
          </Field>

          <Field label="Moteur (backtest complet)">
            <select className="select" value={engine} onChange={(e) => setEngine(e.target.value as Engine)}>
              <option value="vectorized">Vectorisé</option>
              <option value="event_driven">Event-driven</option>
            </select>
          </Field>

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

          <button
            type="button"
            onClick={handleBacktest}
            disabled={isBacktesting || savedStrategyId === null || !symbol || !!paramsError}
            className="mt-1 rounded-md bg-signal px-4 py-2.5 text-sm font-semibold text-bg
                       transition hover:bg-signal/90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isBacktesting ? "Calcul en cours…" : "Lancer le backtest complet"}
          </button>
          {savedStrategyId === null && (
            <span className="text-xs text-ink-faint">
              Sauvegarde la stratégie avant de lancer un backtest complet.
            </span>
          )}
          {backtestError && <span className="text-xs text-down">{backtestError}</span>}

          {strategies.length > 0 && (
            <div className="mt-2 border-t border-border pt-3">
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-muted">
                Stratégies sauvegardées
              </h3>
              <ul className="flex flex-col gap-1">
                {strategies.map((s) => (
                  <li key={s.strategy_id}>
                    <button
                      type="button"
                      onClick={() => loadStrategy(s)}
                      className="w-full rounded-md px-2 py-1.5 text-left text-xs text-ink-muted transition hover:bg-bg-raised hover:text-ink"
                    >
                      {s.name} <span className="text-ink-faint">v{s.latest_version}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {backtestResult && (
        <div className="flex flex-col gap-4">
          <MetricsPanel metrics={backtestResult.metrics} />
          <EquityChart
            equityCurve={backtestResult.equity_curve}
            initialCapital={backtestResult.initial_capital}
          />
        </div>
      )}

      {logs.length > 0 && (
        <div className="rounded-lg border border-border bg-bg-panel p-5">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-muted">
            Journal d&apos;exécution
          </h2>
          <table className="w-full text-left text-xs">
            <thead className="text-ink-faint">
              <tr>
                <th className="pb-2">Date</th>
                <th className="pb-2">Type</th>
                <th className="pb-2">Version</th>
                <th className="pb-2">Statut</th>
                <th className="pb-2">Durée</th>
              </tr>
            </thead>
            <tbody className="tabular">
              {logs.map((l) => (
                <tr key={l.id} className="border-t border-border/60">
                  <td className="py-1.5 text-ink-muted">{l.created_at}</td>
                  <td className="py-1.5">{l.kind === "quick_test" ? "Test rapide" : "Backtest complet"}</td>
                  <td className="py-1.5">v{l.version}</td>
                  <td className={`py-1.5 ${l.status === "ok" ? "text-up" : "text-down"}`}>
                    {STATUS_LABELS[l.status]}
                  </td>
                  <td className="py-1.5 text-ink-muted">{l.execution_time_ms ?? "—"} ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
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