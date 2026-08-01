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
| [Stooq.com](https://stooq.com) | Vérification croisée daily | Non | Export CSV, pas de limite documentée | Sprint 1 |
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

## Scripts de test de connexion

Chaque source dispose d'un script `test_connection_<source>.py` dans
`packages/data-pipeline/`. Lancer tous les tests :

```bash
python packages/data-pipeline/test_all_connections.py
```
