"""
Test de connexion — Binance public data (data.binance.vision), pas de clé requise.
Vérifie que le fichier d'archive daily klines pour BTCUSDT est accessible.
"""
import sys
import requests

# data.binance.vision publie des archives ZIP par jour/mois pour chaque symbole.
# On teste juste l'accessibilité HTTP de l'index du dossier klines BTCUSDT en daily.
TEST_URL = "https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1d/"


def main():
    try:
        resp = requests.get(TEST_URL, timeout=10)
    except Exception as e:
        print(f"[ECHEC] Erreur réseau vers data.binance.vision : {e}")
        sys.exit(1)

    if resp.status_code != 200:
        print(f"[ECHEC] Statut HTTP {resp.status_code} pour {TEST_URL}")
        sys.exit(1)

    print(f"[OK] Binance public data accessible (statut {resp.status_code}), {len(resp.content)} octets reçus")


if __name__ == "__main__":
    main()
