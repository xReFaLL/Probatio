export function fmtNumber(n: number, decimals = 2): string {
  return n.toLocaleString("fr-FR", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

export function fmtCurrency(n: number): string {
  return n.toLocaleString("fr-FR", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

export function fmtPct(n: number, decimals = 1): string {
  return `${(n * 100).toFixed(decimals)} %`;
}

export function fmtDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("fr-FR", { year: "numeric", month: "short", day: "2-digit" });
}

// Convertit un timestamp ISO/"YYYY-MM-DD ..." en secondes epoch UTC pour
// lightweight-charts (qui attend soit "YYYY-MM-DD", soit un UNIX timestamp).
export function toChartTime(iso: string): string {
  return iso.slice(0, 10);
}