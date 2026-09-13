"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Backtest" },
  { href: "/walk-forward", label: "Walk-forward" },
  { href: "/screener", label: "Screener" },
  { href: "/compare", label: "Comparateur" },
  { href: "/portfolio", label: "Portefeuille" },
  { href: "/custom-strategy", label: "Stratégie custom" },
];

export default function NavBar() {
  const pathname = usePathname();

  return (
    <nav className="border-b border-border bg-bg-panel/60">
      <div className="mx-auto flex max-w-7xl items-center gap-1 overflow-x-auto px-4 py-2">
        {LINKS.map((link) => {
          const active = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium transition ${
                active
                  ? "bg-bg-raised text-signal ring-1 ring-signal/40"
                  : "text-ink-muted hover:bg-bg-raised hover:text-ink"
              }`}
            >
              {link.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}