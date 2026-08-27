"use client";

import { useEffect, useState } from "react";
import BacktestForm from "@/components/BacktestForm";
import PriceChart from "@/components/PriceChart";
import EquityChart from "@/components/EquityChart";
import DrawdownChart from "@/components/DrawdownChart";
import MetricsPanel from "@/components/MetricsPanel";
import TradesTable from "@/components/TradesTable";
import HistoryPanel from "@/components/HistoryPanel";
import { ApiError, getBacktest, getInstruments, getOhlcv, listBacktests, runBacktest } from "@/lib/api";
import type { BacktestRequest, Instrument } from "@/lib/types";
import { useBacktestStore } from "@/store/useBacktestStore";

export default function Home() {
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [loadingInstruments, setLoadingInstruments] = useState(true);
  const [loadingOhlcv, setLoadingOhlcv] = useState(false);

  const { result, ohlcv, history, isRunning, error, setResult, setOhlcv, setHistory, prependHistory, setRunning, setError } =
    useBacktestStore();

  useEffect(() => {
    getInstruments()
      .then(setInstruments)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Erreur de chargement des instruments."))
      .finally(() => setLoadingInstruments(false));

    listBacktests().then(setHistory).catch(() => {
      /* l'historique est un bonus — une API neuve sans base n'a simplement rien à montrer */
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadPriceChart(symbol: string, assetClass: BacktestRequest["asset_class"]) {
    setLoadingOhlcv(true);
    try {
      const data = await getOhlcv(symbol, assetClass);
      setOhlcv(data);
    } catch {
      setOhlcv(null);
    } finally {
      setLoadingOhlcv(false);
    }
  }

  async function handleRunBacktest(req: BacktestRequest) {
    setRunning(true);
    setError(null);
    try {
      const r = await runBacktest(req);
      setResult(r);
      prependHistory({
        run_id: r.run_id,
        symbol: r.symbol,
        strategy: r.strategy,
        created_at: new Date().toISOString(),
        final_equity: r.metrics.final_equity,
        sharpe: r.metrics.sharpe,
        total_trades: r.metrics.total_trades,
      });
      await loadPriceChart(r.symbol, r.asset_class);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Le backtest a échoué.");
    } finally {
      setRunning(false);
    }
  }

  async function handleSelectHistory(runId: number) {
    setError(null);
    try {
      const r = await getBacktest(runId);
      setResult(r);
      await loadPriceChart(r.symbol, r.asset_class);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Impossible de recharger ce backtest.");
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">
            Probatio <span className="text-signal">/</span> backtest
          </h1>
          <p className="mt-1 text-sm text-ink-muted">
            Backtest de stratégies sur données historiques gratuites — actions, indices, forex,
            matières premières, crypto.
          </p>
        </div>
      </header>

      {error && (
        <div className="mb-6 rounded-md border border-down/30 bg-down/10 px-4 py-3 text-sm text-down">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[360px_1fr]">
        <aside className="flex flex-col gap-6">
          {loadingInstruments ? (
            <div className="rounded-lg border border-border bg-bg-panel p-5 text-sm text-ink-faint">
              Chargement des instruments disponibles…
            </div>
          ) : instruments.length === 0 ? (
            <div className="rounded-lg border border-border bg-bg-panel p-5 text-sm text-ink-faint">
              Aucun instrument dans l&apos;entrepôt pour l&apos;instant — lance les scripts
              d&apos;ingestion (Sprints 1 à 3) avant de backtester.
            </div>
          ) : (
            <BacktestForm instruments={instruments} isRunning={isRunning} onSubmit={handleRunBacktest} />
          )}

          <HistoryPanel history={history} activeRunId={result?.run_id} onSelect={handleSelectHistory} />
        </aside>

        <section className="flex flex-col gap-6">
          <PriceChart ohlcv={ohlcv} trades={result?.trades ?? []} loading={loadingOhlcv} />

          {result ? (
            <>
              <MetricsPanel metrics={result.metrics} />
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                <EquityChart equityCurve={result.equity_curve} initialCapital={result.initial_capital} />
                <DrawdownChart equityCurve={result.equity_curve} />
              </div>
              <TradesTable trades={result.trades} />
            </>
          ) : (
            <div className="rounded-lg border border-dashed border-border p-10 text-center text-sm text-ink-faint">
              Configure et lance un backtest pour voir apparaître métriques, courbe d&apos;equity,
              drawdown et journal des trades.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}