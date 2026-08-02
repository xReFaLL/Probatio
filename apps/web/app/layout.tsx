import "./globals.css";
import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

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
    <html lang="fr" className={`${inter.variable} ${mono.variable}`}>
      <body className="min-h-screen flex flex-col bg-bg text-ink font-sans antialiased">
        <main className="flex-1">{children}</main>
        <footer className="border-t border-border px-4 py-3 text-xs text-ink-faint text-center">
          Biais de survivance possible sur les actions (tickers radiés absents des sources
          gratuites) · profondeur intraday limitée hors crypto. Graphiques de prix propulsés
          par{" "}
          <a
            href="https://www.tradingview.com"
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-ink-muted"
          >
            TradingView
          </a>
          .
        </footer>
      </body>
    </html>
  );
}