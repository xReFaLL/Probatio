"""
Test de connexion — FRED (Federal Reserve Economic Data), clé API requise
(cf. .env FRED_API_KEY). Limite généreuse.
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FRED_API_KEY")
URL = "https://api.stlouisfed.org/fred/series/observations"


def main():
    if not API_KEY:
        print("[ECHEC] FRED_API_KEY absente du .env")
        sys.exit(1)

    params = {
        "series_id": "CPIAUCSL",  # Indice des prix à la consommation US
        "api_key": API_KEY,
        "file_type": "json",
        "limit": 5,
        "sort_order": "desc",
    }
    try:
        resp = requests.get(URL, params=params, timeout=10)
        payload = resp.json()
    except Exception as e:
        print(f"[ECHEC] Erreur lors de l'appel FRED : {e}")
        sys.exit(1)

    if "observations" not in payload:
        print(f"[ECHEC] Réponse inattendue : {payload}")
        sys.exit(1)

    print(f"[OK] FRED : {len(payload['observations'])} observations récupérées pour CPIAUCSL")


if __name__ == "__main__":
    main()
