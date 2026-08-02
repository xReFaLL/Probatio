"use client";

import { useMemo } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { EquityPoint } from "@/lib/types";
import { fmtDate } from "@/lib/format";

interface Props {
  equityCurve: EquityPoint[];
}

// Le drawdown n'est pas renvoyé point par point par l'API (seul le
// max_drawdown scalaire l'est, dans les métriques) — on le recalcule ici à
// partir de la courbe d'equity, avec la même formule que
// packages/backtest-engine/metrics.py (equity - running_max) / running_max.
export default function DrawdownChart({ equityCurve }: Props) {
  const data = useMemo(() => {
    let runningMax = -Infinity;
    return equityCurve.map((p) => {
      runningMax = Math.max(runningMax, p.equity);
      const drawdown = runningMax > 0 ? (p.equity - runningMax) / runningMax : 0;
      return { date: fmtDate(p.timestamp), drawdown: drawdown * 100 };
    });
  }, [equityCurve]);

  return (
    <div className="rounded-lg border border-border bg-bg-panel p-4">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-ink-muted">Drawdown</h3>
      <ResponsiveContainer width="100%" height={140}>
        <AreaChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="ddFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f16565" stopOpacity={0} />
              <stop offset="100%" stopColor="#f16565" stopOpacity={0.35} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#161d28" vertical={false} />
          <XAxis dataKey="date" tick={{ fill: "#5b6472", fontSize: 11 }} minTickGap={40} axisLine={{ stroke: "#1f2937" }} tickLine={false} />
          <YAxis
            tick={{ fill: "#5b6472", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={48}
            tickFormatter={(v) => `${v}%`}
          />
          <Tooltip
            contentStyle={{ background: "#111720", border: "1px solid #1f2937", borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: "#8a94a3" }}
            formatter={(v: number) => [`${v.toFixed(1)} %`, "Drawdown"]}
          />
          <Area type="monotone" dataKey="drawdown" stroke="#f16565" strokeWidth={1.5} fill="url(#ddFill)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}