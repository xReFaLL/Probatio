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
cp .env.local.example .env.local
npm install
npm run dev

# Ou : tout lancer via Docker Compose
docker compose up --build
```

> `data/` (entrepôt Parquet + `app.db`) n'est jamais commité (voir
> `.gitignore`) — chaque installation régénère ses propres données
> localement via les commandes ci-dessus.

## API (Sprint 5)

Une fois `uvicorn apps.api.main:app --reload` lancé, documentation
interactive sur http://localhost:8000/docs.

- `GET /api/instruments` — instruments disponibles (croisés avec l'entrepôt,
  jamais un symbole sans données).
- `GET /api/instruments/{symbol}/ohlcv` — historique OHLCV d'un instrument
  (params `asset_class` obligatoire, `timeframe`/`start`/`end` optionnels) ;
  sert le graphique de prix du frontend, réutilise `warehouse_reader.load_ohlcv`
  du Sprint 4 telle quelle.
- `POST /api/backtests` — lance un backtest, persiste le résultat, le
  retourne. Stratégies disponibles : `sma_crossover` (params `fast`, `slow`),
  `rsi_mean_reversion` (params `length`, `oversold`, `overbought`).
- `GET /api/backtests` — historique des runs.
- `GET /api/backtests/{run_id}` — relit un run déjà calculé (pas de recalcul).

Exemple :
```bash
curl -X POST http://localhost:8000/api/backtests \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL","asset_class":"equity","strategy":"sma_crossover","params":{"fast":20,"slow":50}}'
```

## API (Sprint 6)

Ajouts au-dessus du Sprint 5 — toujours documentés sur http://localhost:8000/docs.

- `POST /api/backtests` accepte désormais `"engine": "vectorized" | "event_driven"`
  (défaut `vectorized`) et `"position_size"` (fraction du capital par position,
  utilisé uniquement par `event_driven`). Le moteur event-driven simule des
  ordres réels : fill à l'open de la barre suivante ajusté du slippage,
  commission sur la valeur notionnelle réelle, equity mark-to-market à chaque
  barre — plus lent mais plus réaliste que le mode vectorisé.
- `POST /api/walk-forward` — walk-forward analysis. `param_grid` accepte des
  listes de valeurs (`{"fast": [10, 20], "slow": [50, 100]}`) testées par
  produit cartésien sur chaque fenêtre in-sample ; les meilleurs paramètres
  (selon `optimize_metric`) sont appliqués tels quels sur la fenêtre
  out-of-sample suivante. `GET /api/walk-forward` (historique) et
  `GET /api/walk-forward/{id}` (détail).
- `POST /api/screener` — scanne un univers d'instruments (`asset_class` et/ou
  `symbols`, sinon tout l'univers disponible) avec une même stratégie/paramètres
  et classe le résultat par `rank_by`. `GET /api/screener` /
  `GET /api/screener/{id}`.
- `POST /api/compare` — jusqu'à 8 variantes (stratégie + paramètres + moteur)
  sur le même instrument/fenêtre ; chaque variante est un backtest normal
  (retrouvable dans `GET /api/backtests`), le comparateur n'ajoute qu'une
  orchestration côté endpoint.
- `POST /api/portfolio` — combine plusieurs jambes (instrument + stratégie +
  poids) en une courbe d'equity pondérée, avec `rebalance`
  (`none` / `monthly` / `quarterly`). `GET /api/portfolio` /
  `GET /api/portfolio/{id}`.

## Frontend (Sprint 6)

```bash
cd apps/web
cp .env.local.example .env.local   # NEXT_PUBLIC_API_BASE_URL, http://localhost:8000 par défaut
npm install
npm run dev
```

Puis ouvrir http://localhost:3000, avec l'API du dessus lancée en parallèle.
Une barre de navigation en haut relie les cinq outils :

- **`/`** — Backtest simple : formulaire (instrument → stratégie → paramètres
  → moteur vectorisé/event-driven → dates/capital/frais), graphique de prix
  (bougies + marqueurs d'entrée/sortie, TradingView Lightweight Charts),
  courbe d'equity et drawdown (Recharts), métriques, table des trades,
  historique des runs cliquable.
- **`/walk-forward`** — configure une grille de paramètres et des fenêtres
  in-sample/out-of-sample, affiche la courbe out-of-sample recollée et le
  détail de chaque fenêtre (meilleurs paramètres retenus, métriques OOS).
- **`/screener`** — scanne un univers d'instruments avec une stratégie donnée,
  classement triable par métrique, liste des instruments ignorés (pas de
  données, warm-up trop long, etc.).
- **`/compare`** — jusqu'à 8 variantes (stratégie/paramètres/moteur) sur le
  même instrument, courbes d'equity superposées + tableau de métriques.
- **`/portfolio`** — construit un portefeuille multi-jambes (instrument +
  stratégie + poids), avec ou sans rebalancement périodique, courbe d'equity
  combinée + contribution de chaque jambe.

## Feuille de route

- [x] **Sprint 0** — Scaffold, `.env.example`, `LICENSE`, tests de connexion
- [x] **Sprint 1** — Ingestion daily yfinance + vérification croisée Stooq
- [x] **Sprint 2** — Ingestion crypto Binance (historique complet)
- [x] **Sprint 3** — Ingestion macro/fondamentaux (FRED, SEC EDGAR, Alpha Vantage)
- [x] **Sprint 4** — Moteur de backtest vectorisé + indicateurs + stratégies de référence
- [x] **Sprint 5** — API FastAPI + frontend Next.js (formulaire, graphiques, historique)
- [x] **Sprint 6** — Moteur event-driven, walk-forward, screener, comparateur, portefeuille
- [ ] **Sprint 7** — Stratégies custom utilisateur (éditeur Monaco, sandboxing)

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