import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Probatio",
  description: "Plateforme open source de backtest de stratégies de trading",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body className="min-h-screen flex flex-col bg-white text-slate-900">
        <main className="flex-1">{children}</main>
        <footer className="border-t border-slate-200 px-4 py-3 text-xs text-slate-500 text-center">
          Graphiques de prix propulsés par{" "}
          <a
            href="https://www.tradingview.com"
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-slate-700"
          >
            TradingView
          </a>
        </footer>
      </body>
    </html>
  );
}
