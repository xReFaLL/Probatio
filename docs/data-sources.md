# Sources de données — Probatio

Toutes les sources utilisées sont gratuites. Aucune n'est jamais appelée en
direct par le moteur de backtest : un pipeline d'ingestion (voir
`packages/data-pipeline/`) alimente l'entrepôt Parquet local, qui est la seule
source lue au moment du backtest.

| Source | Usage | Clé requise | Limite | Statut |
|---|---|---|---|---|
| [yfinance](https://github.com/ranaroussi/yfinance) | Actions, indices, ETF, forex, commodities — daily profond, intraday limité | Non | Throttling non documenté officiellement, à gérer côté pipeline | Sprint 1 |
| [Binance public data](https://data.binance.vision) | Crypto, historique complet depuis 2017, toutes granularités | Non | Aucune limite pratique | Sprint 2 |
| [Alpha Vantage](https://www.alphavantage.co) | Backup / fondamentaux | Oui | 25 req/jour, 5/min | Sprint 3 |
| [Twelve Data](https://twelvedata.com) | Backup actions/forex/crypto | Oui | 800 crédits/jour, 8/min | Sprint 3 |
| [FRED](https://fred.stlouisfed.org) | Macro (taux, inflation, PIB) | Oui | Généreuse | Sprint 3 |
| [Stooq.com](https://stooq.com) | Vérification croisée daily — **inactif** | Non | Bloque désormais les clients non-navigateur (challenge anti-bot Cloudflare) | Sprint 1, désactivé Sprint 3 |
| [SEC EDGAR](https://www.sec.gov/edgar) | Fondamentaux US | Non | Aucune, mais User-Agent identifiable exigé | Sprint 3 |

## Disclaimers utilisateur (à afficher dans l'app)

- **Biais de survivance** : les listes d'actions (S&P 500, CAC 40) reflètent la
  composition actuelle des indices ; les tickers radiés ou retirés ne sont pas
  disponibles via les sources gratuites utilisées ici. Les backtests sur longue
  période peuvent donc surestimer la performance réelle historique.
- **Profondeur intraday limitée** : hors crypto (Binance), l'historique
  intraday disponible via les sources gratuites est réduit (quelques semaines
  à quelques mois selon la source). Les backtests intraday longue période ne
  sont fiables que sur crypto.
- **Usage personnel/recherche uniquement** : les données Yahoo/yfinance sont
  utilisées dans le respect de leurs conditions d'usage ; aucune redistribution
  commerciale des données brutes n'est faite dans ce dépôt.

## Univers embarqué (Sprint 1)

Listes statiques dans `packages/data-pipeline/universe.py` :

- **S&P 500** : 503 lignes (2 classes d'actions pour Alphabet, Fox
  Corporation, News Corp). Composition figée à titre indicatif — à recouper
  périodiquement (rebalancements trimestriels S&P Dow Jones Indices).
- **CAC 40** : 40 valeurs, tickers Euronext Paris (`.PA`).
- **Indices** : S&P 500 (`^GSPC`), Nasdaq Composite (`^IXIC`), CAC 40 (`^FCHI`).
- **Forex** : 6 paires majeures (`EURUSD=X`, etc.).
- **Commodities** : Or, Pétrole WTI, Argent (tickers futures `=F`).
- **Crypto** : 28 paires USDT Binance (ingestion Sprint 2).

## Pipeline d'ingestion daily (Sprint 1)

`packages/data-pipeline/ingest_yfinance.py` télécharge l'historique daily
complet disponible (`period="max"`) pour chaque symbole actions/indices/forex/
commodities et écrit dans l'entrepôt Parquet via
`packages/data-pipeline/parquet_writer.py`, qui partitionne par année et
déduplique sur `timestamp` (dernière valeur `ingested_at` gagne, donc les
ré-exécutions sont sûres — idempotentes).

`packages/data-pipeline/verify_cross_check_stooq.py` comparait à l'origine le
dernier close de l'entrepôt à celui de Stooq pour un échantillon de 5 actions
US, avec une tolérance de 1 % (petits écarts possibles liés aux ajustements de
dividendes/splits selon la source).

**Mise à jour Sprint 3** : Stooq bloque désormais les clients HTTP
non-navigateur via un challenge anti-bot Cloudflare (page "vérification du
navigateur" au lieu du CSV attendu), indépendamment du User-Agent envoyé. Ce
n'est plus une source fiable pour un pipeline automatisé. La vérification
croisée daily utilise donc maintenant
`packages/data-pipeline/verify_cross_check_twelvedata.py`, qui reprend
exactement la même logique (même échantillon, même tolérance 1 %) mais
interroge Twelve Data — déjà intégré comme source backup, donc aucune
nouvelle dépendance. `verify_cross_check_stooq.py` et
`test_connection_stooq.py` restent dans le repo pour référence mais Stooq est
passé en source optionnelle (non-bloquante) dans
`test_all_connections.py`.

## Pipeline d'ingestion crypto (Sprint 2)

`packages/data-pipeline/ingest_binance.py` télécharge l'historique complet
disponible sur data.binance.vision pour chaque paire de `universe.CRYPTO_PAIRS`,
et écrit dans l'entrepôt Parquet via `parquet_writer.py` (même mécanisme
d'idempotence par déduplication sur `timestamp` qu'au Sprint 1).

Points clés :

- **Archives mensuelles + quotidiennes**, pas d'appel à l'API REST classique
  (`api.binance.com`) : data.binance.vision est un espace de fichiers
  statiques (klines pré-calculées), sans limite de débit documentée. Le gros
  de l'historique (2017 -> mois dernier complet) est récupéré via les
  archives mensuelles (~1 fichier/mois/paire) ; le mois en cours est complété
  via les archives quotidiennes.
- Téléchargements **parallélisés** (10 workers) par paire — cohérent avec le
  principe "aucune limite pratique" de cette source (contrairement à
  Alpha Vantage/Twelve Data, qui restent strictement séquentiels et throttlés
  au Sprint 3).
- Un **404** sur un mois antérieur à la cotation d'une paire est normal (ex :
  `TIAUSDT`, `SUIUSDT` n'existaient pas en 2018) et n'est pas traité comme un
  échec ; seule l'absence totale de données pour une paire est reportée en
  échec.
- **Normalisation des timestamps** : les archives historiques encodent
  `open_time` en millisecondes, mais Binance a basculé une partie des
  archives récentes en microsecondes — le script détecte l'unité par ordre
  de grandeur et normalise systématiquement en millisecondes avant écriture.
- **Format CSV** : gère à la fois les archives sans en-tête (format
  historique) et celles avec en-tête explicite (format plus récent).
- Timeframe par défaut : `1d`, cohérent avec le reste de l'entrepôt au MVP.
  Le script accepte `--interval` pour ingérer d'autres granularités
  disponibles sur Binance (ex: `1h`) sans modification de code, en vue du
  mode intraday (Sprint 6).

## Pipeline d'ingestion macro (Sprint 3)

`packages/data-pipeline/ingest_fred.py` télécharge l'historique complet de
19 séries FRED (`universe.MACRO_SERIES`) couvrant taux directeurs/
obligataires, inflation, PIB, emploi, masse monétaire, logement, sentiment
consommateur et volatilité (VIX).

**Choix par défaut (non spécifié dans le brief)** : FRED renvoie des séries
scalaires (une valeur par date), pas des chandeliers OHLCV. Plutôt que
d'ajouter un schéma dédié, la valeur est dupliquée dans `open/high/low/close`
et `volume=0`, ce qui permet de réutiliser tel quel l'entrepôt Parquet et
`parquet_writer.write_ohlcv` — un point d'accès DuckDB unique pour toutes les
séries temporelles du projet (marché ou macro), utile pour les corrélations
futures (Sprint 6). `asset_class="macro"`.

Le `timeframe` de partitionnement n'est pas fixé à `1d` comme les autres
pipelines : il est dérivé de la fréquence native de chaque série FRED
(`frequency_short` de l'API — mensuelle pour CPIAUCSL, quotidienne pour
DGS10, trimestrielle pour GDP...), via `FREQUENCY_MAP` dans le script.

## Pipeline d'ingestion fondamentaux (Sprint 3)

Deux sources complémentaires, toutes deux restreintes à l'univers **S&P 500
uniquement** — le CAC 40 (Euronext Paris) est hors périmètre : SEC EDGAR ne
couvre que les émetteurs déposant auprès du régulateur américain, et la
couverture fondamentaux gratuite d'Alpha Vantage sur les valeurs Euronext
n'est pas fiable.

- **`ingest_secedgar.py`** (fichier ajouté, absent de l'arborescence initiale
  du brief — nécessaire pour couvrir la source SEC EDGAR assignée à ce
  sprint) : récupère des métriques US-GAAP brutes (chiffre d'affaires,
  résultat net, actifs/passifs, capitaux propres, BPA, actions en
  circulation) via l'endpoint `companyconcept`, avec repli sur des tags XBRL
  alternatifs quand le tag principal n'est pas rapporté (ex : bascule de
  nommage du chiffre d'affaires après l'adoption d'ASC 606). Illimité mais
  User-Agent identifiable obligatoire (`SEC_EDGAR_USER_AGENT`) et débit
  volontairement mesuré (~7 req/s) par prudence, la SEC surveillant
  activement les abus contrairement à data.binance.vision.
- **`ingest_alphavantage.py`** : complète avec les ratios de valorisation
  dérivés du cours qu'un filing SEC brut ne calcule pas (PE, PEG, Beta,
  marges...), via l'endpoint `OVERVIEW`. Limite stricte de 25 requêtes/jour,
  5/min : une ingestion complète des 503 titres en une exécution est
  impossible. Le script traite un lot borné (20 par défaut) et persiste sa
  progression dans un curseur JSON (`data/raw/alphavantage_fundamentals_cursor.json`),
  pour un cycle roulant sur plusieurs exécutions quotidiennes (~26 jours pour
  couvrir tout le S&P 500, puis le cycle recommence — cohérent avec la
  fréquence trimestrielle de publication des fondamentaux).

**Choix par défaut (non spécifié dans le brief)** : le schéma SQLite du
brief ne prévoit pas de table pour ces données. Une table `fundamentals` a
été ajoutée (`packages/data-pipeline/fundamentals_db.py`, schéma également
exécuté par `init_db.py`) plutôt que de les stocker dans l'entrepôt Parquet :
les métriques sont hétérogènes selon la source et rapportées à fréquence
irrégulière, ce qui correspond mal au partitionnement `{symbol}/{timeframe}/{year}`
pensé pour des séries OHLCV homogènes. Format long (une ligne par métrique),
upsert idempotent par `(instrument_id, source, metric, period_end)`.

## Scripts de test de connexion

Chaque source dispose d'un script `test_connection_<source>.py` dans
`packages/data-pipeline/`. Lancer tous les tests :

```bash
python packages/data-pipeline/test_all_connections.py
```

## Bilan de santé de l'entrepôt

Les tests de connexion vérifient seulement que les APIs répondent — pas que
les données ingérées sont réellement présentes et saines. Avant de passer au
Sprint 4 (moteur de backtest, qui lit exclusivement l'entrepôt), lancer :

```bash
python packages/data-pipeline/check_warehouse_health.py
```

Ce script compare l'entrepôt Parquet et `data/app.db` à l'univers attendu
(`universe.py`) : couverture des symboles, plages de dates, valeurs OHLC
manquantes. Voir le docstring du script pour l'interprétation des résultats.
