# Probatio

Plateforme web **open source** de backtest de stratégies de trading, basée
exclusivement sur des sources de données gratuites (actions, crypto, forex,
matières premières, macro), sur 20-30 ans d'historique et plusieurs
timeframes.

## Stack

| Couche | Choix |
|---|---|
| Backend | Python 3.11+, FastAPI |
| Entrepôt marché | Parquet + DuckDB |
| Métadonnées | SQLite (mono-utilisateur, MVP) |
| Frontend | Next.js 14+ (App Router), TypeScript, Tailwind, shadcn/ui |
| Graphiques prix | TradingView Lightweight Charts |
| Graphiques perf | Recharts |
| Indicateurs | pandas-ta-classic |
| Moteur de backtest | Maison (pandas/numpy/numba) — vectorisé puis event-driven |
| Ordonnancement | APScheduler |
| Conteneurisation | Docker Compose |

Voir [`docs/data-sources.md`](docs/data-sources.md) pour le détail des sources
de données et leurs limites.

## Démarrage rapide

```bash
# 1. Copier et compléter les variables d'environnement
cp .env.example .env

# 2. Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python packages/data-pipeline/init_db.py          # initialise le schéma SQLite
python packages/data-pipeline/test_all_connections.py  # vérifie l'accès aux sources
python packages/data-pipeline/ingest_yfinance.py --limit 10  # test rapide (10 symboles)
python packages/data-pipeline/ingest_yfinance.py             # ingestion complète (503 + 40 + 3 + 6 + 3 symboles)
python packages/data-pipeline/verify_cross_check_stooq.py    # vérification croisée d'un échantillon
uvicorn apps.api.main:app --reload

# 3. Frontend
cd apps/web
npm install
npm run dev

# Ou : tout lancer via Docker Compose
docker compose up --build
```

## Feuille de route

- [x] **Sprint 0** — Scaffold, `.env.example`, `LICENSE`, tests de connexion
- [x] **Sprint 1** — Ingestion daily yfinance + vérification croisée Stooq
- [ ] **Sprint 2** — Ingestion crypto Binance (historique complet)
- [ ] **Sprint 3** — Ingestion macro/fondamentaux (FRED, SEC EDGAR, Alpha Vantage)
- [ ] **Sprint 4** — Moteur de backtest vectorisé + indicateurs + stratégies de référence
- [ ] **Sprint 5** — API FastAPI + frontend Next.js (charts + config de stratégie)
- [ ] **Sprint 6** — Moteur event-driven, walk-forward, screener, comparateur, portefeuille

## Avertissements (biais connus)

- **Biais de survivance** sur les actions : les tickers radiés/retirés des
  indices ne sont pas disponibles via les sources gratuites utilisées.
- **Profondeur intraday limitée** hors crypto.

Voir `docs/data-sources.md` pour le détail.

## Licence

MIT — voir [`LICENSE`](LICENSE). Les graphiques de prix utilisent TradingView
Lightweight Charts (Apache 2.0) ; l'attribution requise par la licence est
affichée dans le footer de l'application.

Usage personnel/recherche des données Yahoo/yfinance uniquement — pas de
redistribution commerciale des données brutes dans ce dépôt.
