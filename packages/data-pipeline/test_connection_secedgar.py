"""
Test de connexion — SEC EDGAR (pas de clé requise, mais exige un User-Agent
identifiable selon les conditions d'usage de la SEC).

Mis à jour au Sprint 3 : lit SEC_EDGAR_USER_AGENT depuis .env (même variable
qu'ingest_secedgar.py) plutôt qu'une valeur codée en dur, pour rester
cohérent avec l'identité réellement envoyée lors de l'ingestion.
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

URL = "https://data.sec.gov/submissions/CIK0000320193.json"  # Apple Inc.
HEADERS = {
    "User-Agent": os.getenv("SEC_EDGAR_USER_AGENT", "Probatio research contact@example.com")
}


def main():
    try:
        resp = requests.get(URL, headers=HEADERS, timeout=10)
    except Exception as e:
        print(f"[ECHEC] Erreur réseau vers SEC EDGAR : {e}")
        sys.exit(1)

    if resp.status_code != 200:
        print(f"[ECHEC] Statut HTTP {resp.status_code} — vérifier le User-Agent")
        sys.exit(1)

    payload = resp.json()
    name = payload.get("name", "?")
    print(f"[OK] SEC EDGAR accessible : entité '{name}' récupérée")


if __name__ == "__main__":
    main()
