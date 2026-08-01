"""
Test de connexion — Stooq.com (export CSV, pas de clé requise).
Utilisé pour vérification croisée daily.

Correction (retour Sprint 0) : Stooq renvoie 404 aux requêtes sans en-tête
User-Agent de navigateur (anti-scraping). On envoie donc un User-Agent
explicite. Stooq applique aussi un quota quotidien de requêtes assez bas
("Exceeded the daily hits limit") — à utiliser avec parcimonie.
"""
import sys
import io
import csv
import requests

URL = "https://stooq.com/q/d/l/?s=aapl.us&i=d"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


def main():
    try:
        resp = requests.get(URL, headers=HEADERS, timeout=10)
    except Exception as e:
        print(f"[ECHEC] Erreur réseau vers Stooq : {e}")
        sys.exit(1)

    if resp.status_code != 200:
        print(f"[ECHEC] Statut HTTP {resp.status_code} pour {URL}")
        sys.exit(1)

    text = resp.text.strip()

    if "Exceeded the daily hits limit" in text:
        print("[ECHEC] Quota quotidien Stooq dépassé — réessayer demain")
        sys.exit(1)

    if not text.startswith("Date"):
        print(f"[ECHEC] Réponse inattendue de Stooq : {text[:200]!r}")
        sys.exit(1)

    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    print(f"[OK] Stooq : {len(rows) - 1} lignes daily récupérées pour AAPL.US")


if __name__ == "__main__":
    main()
