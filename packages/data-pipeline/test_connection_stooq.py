"""
Test de connexion — Stooq.com (export CSV, pas de clé requise).
Utilisé pour vérification croisée daily.

Mise à jour (retour Sprint 3) : Stooq a mis en place une protection anti-bot
(challenge Cloudflare) qui bloque les clients HTTP simples, indépendamment du
User-Agent envoyé — ce n'est plus un problème de "404 sans bon header" comme
au Sprint 0. On ne tente pas de contourner cette protection (proxy, navigateur
headless furtif, etc.) : ce script se contente de diagnostiquer clairement le
cas pour ne pas le confondre avec une vraie panne réseau ou un dépassement de
quota.
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

    if "verify your browser" in text.lower() or "noscript" in text.lower():
        print(
            "[ECHEC] Stooq bloque les clients non-navigateur (challenge anti-bot). "
            "Connu et attendu depuis le Sprint 3 — voir docs/data-sources.md. "
            "Pas un bug réseau, pas la peine de relancer."
        )
        sys.exit(1)

    if not text.startswith("Date"):
        print(f"[ECHEC] Réponse inattendue de Stooq : {text[:200]!r}")
        sys.exit(1)

    reader = list(csv.reader(io.StringIO(text)))
    print(f"[OK] Stooq : {len(reader) - 1} lignes daily récupérées pour AAPL.US")


if __name__ == "__main__":
    main()
