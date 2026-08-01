"""
Test de connexion — Stooq.com (export CSV, pas de clé requise).
Utilisé pour vérification croisée daily.
"""
import sys
import requests
import io
import csv

URL = "https://stooq.com/q/d/l/?s=aapl.us&i=d"


def main():
    try:
        resp = requests.get(URL, timeout=10)
    except Exception as e:
        print(f"[ECHEC] Erreur réseau vers Stooq : {e}")
        sys.exit(1)

    if resp.status_code != 200 or not resp.text.startswith("Date"):
        print(f"[ECHEC] Réponse inattendue de Stooq (statut {resp.status_code})")
        sys.exit(1)

    reader = csv.reader(io.StringIO(resp.text))
    rows = list(reader)
    print(f"[OK] Stooq : {len(rows) - 1} lignes daily récupérées pour AAPL.US")


if __name__ == "__main__":
    main()
