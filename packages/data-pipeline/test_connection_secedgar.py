"""
Test de connexion — SEC EDGAR (pas de clé requise, mais exige un User-Agent
identifiable selon les conditions d'usage de la SEC).
"""
import sys
import requests

URL = "https://data.sec.gov/submissions/CIK0000320193.json"  # Apple Inc.
HEADERS = {
    # La SEC exige un User-Agent avec contact — à personnaliser avant mise en prod.
    "User-Agent": "Probatio research contact@example.com"
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
