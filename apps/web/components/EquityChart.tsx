"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { EquityPoint } from "@/lib/types";
import { fmtCurrency, fmtDate } from "@/lib/format";

interface Props {
  equityCurve: EquityPoint[];
  initialCapital: number;
}

export default function EquityChart({ equityCurve, initialCapital }: Props) {
  const data = equityCurve.map((p) => ({ ...p, date: fmtDate(p.timestamp) }));
  const isUp = (data.at(-1)?.equity ?? initialCapital) >= initialCapital;

  return (
    <div className="rounded-lg border border-border bg-bg-panel p-4">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-ink-muted">
        Courbe d&apos;equity
      </h3>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={isUp ? "#2dd4a5" : "#f16565"} stopOpacity={0.35} />
              <stop offset="100%" stopColor={isUp ? "#2dd4a5" : "#f16565"} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#161d28" vertical={false} />
          <XAxis dataKey="date" tick={{ fill: "#5b6472", fontSize: 11 }} minTickGap={40} axisLine={{ stroke: "#1f2937" }} tickLine={false} />
          <YAxis
            tick={{ fill: "#5b6472", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={70}
            tickFormatter={(v) => fmtCurrency(v)}
          />
          <Tooltip
            contentStyle={{ background: "#111720", border: "1px solid #1f2937", borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: "#8a94a3" }}
            formatter={(v: number) => [fmtCurrency(v), "Equity"]}
          />
          <Area
            type="monotone"
            dataKey="equity"
            stroke={isUp ? "#2dd4a5" : "#f16565"}
            strokeWidth={1.5}
            fill="url(#equityFill)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}