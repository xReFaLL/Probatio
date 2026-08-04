# Probatio

Plateforme web open source de backtest de stratégies de trading, basée
exclusivement sur des sources de données **gratuites** (actions, crypto,
forex, matières premières, macro), sur 20-30 ans d'historique, plusieurs
timeframes. MIT.

> ⚠️ Biais de survivance sur les actions (tickers radiés absents des sources
> gratuites) et profondeur intraday très limitée hors crypto — voir
> `docs/data-sources.md`.

## Stack

| Composant | Choix |
|---|---|
| Backend | Python 3.11+, FastAPI |
| Entrepôt marché | Parquet, interrogé via DuckDB |
| Métadonnées applicatives | SQLite (`data/app.db`) |
| Frontend | Next.js 14 (App Router), TypeScript, TailwindCSS, shadcn/ui |
| Graphiques prix | TradingView Lightweight Charts |
| Graphiques performance | Recharts |
| Indicateurs techniques | pandas-ta-classic |
| Moteur de backtest | Fait maison (pandas/numpy/numba) — vectorisé + event-driven |
| Ordonnancement ingestion | APScheduler |
| Stratégies custom (Sprint 7) | Éditeur Monaco + sandbox subprocess isolé |
| Conteneurisation | Docker Compose |

## Démarrage rapide

### Avec Docker (recommandé)

```bash
cp .env.example .env   # renseigner les clés Alpha Vantage / Twelve Data / FRED
docker compose up --build
```

- API : http://localhost:8000 (docs OpenAPI sur `/docs`)
- Web : http://localhost:3000

### En local, sans Docker

```bash
# Backend
python3 -m venv .venv && source .venv/bin/activate # si vous voulez utiliser venv sinon ce n'est pas obligatore
pip install -r requirements.txt
python packages/data-pipeline/init_db.py        # crée data/app.db
uvicorn apps.api.main:app --reload --app-dir .  # ou voir apps/api/Dockerfile

# Frontend (dans un autre terminal)
cd apps/web
npm install
npm run dev
```

## Ingestion des données

Aucune API n'est jamais appelée en direct par le moteur de backtest — un
pipeline d'ingestion tourne en tâche de fond, respecte les rate limits de
chaque source, et alimente l'entrepôt Parquet local :

```bash
python packages/data-pipeline/ingest_yfinance.py       # actions, indices, forex, commodities
python packages/data-pipeline/ingest_binance.py        # crypto (historique complet)
python packages/data-pipeline/ingest_fred.py           # macro
python packages/data-pipeline/ingest_alphavantage.py   # backup / fondamentaux
```

Détail des sources, limites de rate-limit et clauses d'usage :
`docs/data-sources.md`.

## Fonctionnalités

- **Backtest** — moteur vectorisé (prototypage rapide) et event-driven
  (slippage, commissions, sizing réaliste), stratégies internes (croisement
  de moyennes mobiles, RSI mean-reversion).
- **Walk-forward analysis** — optimisation in-sample / validation out-of-sample.
- **Screener** — passe une stratégie sur tout un univers de titres, classe
  par métrique.
- **Comparateur** — plusieurs stratégies/instruments côte à côte.
- **Portefeuille multi-actifs** — plusieurs legs pondérés, rebalancement.
- **Stratégies custom** (`/custom-strategy`) — éditeur Monaco intégré,
  contrat `generate_signals(df, params)` (vectorisé) ou
  `on_bar(context, bar)` (event-driven), test rapide sur échantillon avant
  backtest complet. Le code utilisateur tourne dans un sandbox isolé
  (subprocess séparé, imports restreints à pandas/numpy/pandas-ta-classic,
  sans accès réseau ni disque, CPU/mémoire/temps plafonnés) — voir
  `packages/backtest-engine/sandbox/`.

## Structure du repo

```
probatio/
├── apps/
│   ├── web/                        # Next.js
│   └── api/                        # FastAPI
├── packages/
│   ├── data-pipeline/               # ingestion + schéma SQLite
│   └── backtest-engine/             # moteurs, indicateurs, métriques, sandbox
├── data/
│   ├── raw/                        # gitignored
│   ├── warehouse/                  # Parquet, partitionné asset_class/symbol/timeframe/year
│   └── app.db                      # SQLite
├── docs/
│   └── data-sources.md
├── .env.example
├── docker-compose.yml
└── LICENSE
```

## Développement

```bash
# Type-check complet du frontend
cd apps/web && npx tsc --noEmit

# Compilation Python (détection d'erreurs de syntaxe)
python -m py_compile packages/backtest-engine/**/*.py apps/api/*.py
```

## Licence

MIT — voir `LICENSE`. Les données Yahoo/yfinance sont soumises à leurs
propres clauses d'usage personnel/recherche : pas de redistribution
commerciale des données brutes dans ce repo.