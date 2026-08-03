"""
Test de connexion — Twelve Data (clé API requise, cf. .env TWELVEDATA_API_KEY).
Limite : 800 crédits/jour, 8/min — ce script ne fait qu'UN seul appel léger.
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("TWELVEDATA_API_KEY")
URL = "https://api.twelvedata.com/time_series"


def main():
    if not API_KEY:
        print("[ECHEC] TWELVEDATA_API_KEY absente du .env")
        sys.exit(1)

    params = {
        "symbol": "AAPL",
        "interval": "1day",
        "outputsize": 5,
        "apikey": API_KEY,
    }
    try:
        resp = requests.get(URL, params=params, timeout=10)
        payload = resp.json()
    except Exception as e:
        print(f"[ECHEC] Erreur lors de l'appel Twelve Data : {e}")
        sys.exit(1)

    if payload.get("status") == "error" or "values" not in payload:
        print(f"[ECHEC] Réponse inattendue : {payload}")
        sys.exit(1)

    print(f"[OK] Twelve Data : {len(payload['values'])} points daily récupérés pour AAPL")


if __name__ == "__main__":
    main()
