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
(si sur linux : python -m venv .venv && source .venv/bin/activate)
(si sur windows directement :
pip install -r requirements.txt
python packages/data-pipeline/init_db.py               # initialise le schéma SQLite
python packages/data-pipeline/test_all_connections.py  # vérifie l'accès aux sources (Stooq optionnel, voir docs/data-sources.md)

# Ingestion — chaque script accepte --limit N (test rapide) et --only <classe> ;
# ingest_yfinance.py accepte aussi --symbols pour une re-ingestion ciblée.
python packages/data-pipeline/ingest_yfinance.py              # actions + indices + forex + commodities (~15-25 min)
python packages/data-pipeline/verify_cross_check_twelvedata.py  # vérification croisée d'un échantillon
python packages/data-pipeline/ingest_binance.py               # crypto, historique complet depuis 2017
python packages/data-pipeline/ingest_fred.py                  # 19 séries macro (taux, inflation, PIB, emploi...)
python packages/data-pipeline/ingest_secedgar.py              # fondamentaux SEC EDGAR (S&P 500, pas de limite)
python packages/data-pipeline/ingest_alphavantage.py          # fondamentaux backup, ~20 tickers/jour (quota 25/jour) — à relancer chaque jour pour couvrir tout l'univers

# Vérifier que tout s'est bien passé avant de construire dessus :
python packages/data-pipeline/check_warehouse_health.py

# Valider le moteur de backtest sur un échantillon (Sprint 4) :
python packages/backtest-engine/run_reference_strategies.py

uvicorn apps.api.main:app --reload

# 3. Frontend
cd apps/web
npm install
npm run dev

# Ou : tout lancer via Docker Compose
docker compose up --build
```

> `data/` (entrepôt Parquet + `app.db`) n'est jamais commité (voir
> `.gitignore`) — chaque installation régénère ses propres données
> localement via les commandes ci-dessus.

## Feuille de route

- [x] **Sprint 0** — Scaffold, `.env.example`, `LICENSE`, tests de connexion
- [x] **Sprint 1** — Ingestion daily yfinance + vérification croisée Stooq
- [x] **Sprint 2** — Ingestion crypto Binance (historique complet)
- [x] **Sprint 3** — Ingestion macro/fondamentaux (FRED, SEC EDGAR, Alpha Vantage)
- [x] **Sprint 4** — Moteur de backtest vectorisé + indicateurs + stratégies de référence
- [ ] **Sprint 5** — API FastAPI + frontend Next.js (charts + config de stratégie)
- [ ] **Sprint 6** — Moteur event-driven, walk-forward, screener, comparateur, portefeuille

## Avertissements (biais connus)

- **Biais de survivance** sur les actions : les tickers radiés/retirés des
  indices ne sont pas disponibles via les sources gratuites utilisées.
- **Profondeur intraday limitée** hors crypto.
- **Stooq** (vérification croisée) bloque désormais les clients automatisés
  (protection anti-bot) — source passée en optionnel, remplacée par Twelve
  Data pour la vérification croisée. Voir `docs/data-sources.md`.

Voir `docs/data-sources.md` pour le détail.

## Licence

MIT — voir [`LICENSE`](LICENSE). Les graphiques de prix utilisent TradingView
Lightweight Charts (Apache 2.0) ; l'attribution requise par la licence est
affichée dans le footer de l'application.

Usage personnel/recherche des données Yahoo/yfinance uniquement — pas de
redistribution commerciale des données brutes dans ce dépôt.
