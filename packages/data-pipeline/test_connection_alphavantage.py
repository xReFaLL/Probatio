"""
Test de connexion — Alpha Vantage (clé API requise, cf. .env ALPHAVANTAGE_API_KEY).
Limite : 25 requêtes/jour, 5/min — ce script ne fait qu'UN seul appel.
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
URL = "https://www.alphavantage.co/query"


def main():
    if not API_KEY:
        print("[ECHEC] ALPHAVANTAGE_API_KEY absente du .env")
        sys.exit(1)

    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": "AAPL",
        "outputsize": "compact",
        "apikey": API_KEY,
    }
    try:
        resp = requests.get(URL, params=params, timeout=10)
        payload = resp.json()
    except Exception as e:
        print(f"[ECHEC] Erreur lors de l'appel Alpha Vantage : {e}")
        sys.exit(1)

    if "Time Series (Daily)" not in payload:
        print(f"[ECHEC] Réponse inattendue (quota atteint ? clé invalide ?) : {payload}")
        sys.exit(1)

    n_points = len(payload["Time Series (Daily)"])
    print(f"[OK] Alpha Vantage : {n_points} points daily récupérés pour AAPL")


if __name__ == "__main__":
    main()
