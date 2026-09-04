# backtest-engine

Moteur de backtest maison (pandas + numpy + numba), sans dépendance à
backtrader/vectorbt/zipline.

- `warehouse_reader.py` — chargement OHLCV depuis l'entrepôt Parquet, seul
  point d'entrée disque du package. **Sprint 4**
- `indicators.py` — wrapper autour de `pandas-ta-classic`. **Sprint 4**
- `strategies.py` — stratégies de référence (croisement de moyennes
  mobiles, RSI) utilisées pour valider le moteur. **Sprint 4**
- `engine_vectorized.py` — mode vectorisé (prototypage rapide), décalage
  d'une barre, commission/slippage simplifiés. **Sprint 4**
- `metrics.py` — Sharpe, Sortino, max drawdown, win rate, profit factor —
  clés alignées sur la table SQLite `backtest_results`. **Sprint 4**
- `run_reference_strategies.py` — script de validation bout-en-bout,
  lance les stratégies de référence sur un échantillon et affiche les
  métriques. **Sprint 4**
- `engine_event_driven.py` — mode event-driven (simulation d'ordres
  réaliste avec slippage/commissions). **Sprint 6**, pas encore implémenté.

Usage rapide :
```bash
python packages/backtest-engine/run_reference_strategies.py
```