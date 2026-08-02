import type { Config } from "tailwindcss";

// Palette "terminal de marché" : fond quasi noir à dominante bleue, un seul
// accent (teal signal) plutôt que la routine crème+terracotta ou
// noir+néon — choisi pour ce projet de backtest, pas un défaut générique.
const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: "#0a0e13",
          panel: "#111720",
          raised: "#161d28",
        },
        border: {
          DEFAULT: "#1f2937",
          subtle: "#161d28",
        },
        ink: {
          DEFAULT: "#e6edf3",
          muted: "#8a94a3",
          faint: "#5b6472",
        },
        signal: {
          DEFAULT: "#22d3b6",
          dim: "#0f766e",
        },
        up: "#2dd4a5",
        down: "#f16565",
        warn: "#f5a623",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;