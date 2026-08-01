# backtest-engine

Moteur de backtest maison (pandas + numpy + numba), sans dépendance à
backtrader/vectorbt/zipline.

- `engine_vectorized.py` — mode vectorisé (prototypage rapide). **Sprint 4**
- `engine_event_driven.py` — mode event-driven (validation réaliste avec
  slippage/commissions/ordres). **Sprint 6**
- `indicators.py` — wrapper autour de `pandas-ta-classic`. **Sprint 4**
- `metrics.py` — Sharpe, Sortino, max drawdown, win rate, profit factor, etc.
  **Sprint 4**

Ces fichiers sont volontairement vides au Sprint 0 — ils seront implémentés au
Sprint 4 (moteur vectorisé) et Sprint 6 (moteur event-driven).
