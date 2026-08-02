"use client";

import { useEffect, useRef } from "react";
import {
  ColorType,
  CrosshairMode,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type SeriesMarker,
  type Time,
} from "lightweight-charts";
import type { OHLCVResponse, Trade } from "@/lib/types";
import { toChartTime } from "@/lib/format";

interface Props {
  ohlcv: OHLCVResponse | null;
  trades: Trade[];
  loading: boolean;
}

export default function PriceChart({ ohlcv, trades, loading }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  // Création du chart une seule fois, sur le montage du composant.
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#8a94a3",
        fontFamily: "var(--font-mono)",
      },
      grid: {
        vertLines: { color: "#161d28" },
        horzLines: { color: "#161d28" },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "#1f2937" },
      timeScale: { borderColor: "#1f2937", timeVisible: false },
      autoSize: true,
    });

    const series = chart.addCandlestickSeries({
      upColor: "#2dd4a5",
      downColor: "#f16565",
      borderVisible: false,
      wickUpColor: "#2dd4a5",
      wickDownColor: "#f16565",
    });

    chartRef.current = chart;
    seriesRef.current = series;

    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  // Mise à jour des données de prix.
  useEffect(() => {
    if (!seriesRef.current || !ohlcv) return;
    const data = ohlcv.points.map((p) => ({
      time: toChartTime(p.timestamp) as Time,
      open: p.open,
      high: p.high,
      low: p.low,
      close: p.close,
    }));
    seriesRef.current.setData(data);
    chartRef.current?.timeScale().fitContent();
  }, [ohlcv]);

  // Marqueurs d'entrée (flèche verte vers le haut) / sortie (flèche rouge
  // vers le bas) pour chaque trade du backtest affiché.
  useEffect(() => {
    if (!seriesRef.current) return;
    const markers: SeriesMarker<Time>[] = trades
      .flatMap((t) => [
        {
          time: toChartTime(t.entry_time) as Time,
          position: "belowBar" as const,
          color: "#2dd4a5",
          shape: "arrowUp" as const,
          text: "Entrée",
        },
        {
          time: toChartTime(t.exit_time) as Time,
          position: "aboveBar" as const,
          color: t.pnl >= 0 ? "#2dd4a5" : "#f16565",
          shape: "arrowDown" as const,
          text: "Sortie",
        },
      ])
      .sort((a, b) => (a.time as string).localeCompare(b.time as string));
    seriesRef.current.setMarkers(markers);
  }, [trades]);

  return (
    <div className="relative h-[420px] w-full rounded-lg border border-border bg-bg-panel p-3">
      {!ohlcv && !loading && (
        <div className="absolute inset-0 flex items-center justify-center text-sm text-ink-faint">
          Lance un backtest pour afficher le graphique de prix.
        </div>
      )}
      {loading && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-bg-panel/60 text-sm text-ink-muted">
          Chargement des données de marché…
        </div>
      )}
      <div ref={containerRef} className="h-full w-full" />
    </div>
  );
}