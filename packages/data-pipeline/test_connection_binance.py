"""
Test de connexion — Binance public data (data.binance.vision), pas de clé requise.

Correction (retour Sprint 3) : l'ancien test interrogeait l'endpoint de
listing S3 (?prefix=...) qui renvoyait auparavant du XML brut
(ListBucketResult). Cet endpoint sert désormais une page HTML de navigation
("Binance Data Collection"), ce qui casse un parsing XML strict — alors que
le mécanisme réellement utilisé par ingest_binance.py (téléchargement direct
de fichiers à URL déterministe, data/spot/{monthly,daily}/klines/{symbol}/
{interval}/...) n'a pas changé et continue de fonctionner (vérifié).

On teste donc la connectivité de la même façon que le pipeline réel :
téléchargement direct d'un petit fichier connu pour exister (le .CHECKSUM
d'une archive mensuelle ancienne — BTCUSDT existe depuis le lancement de
Binance, ce mois ne sera jamais retiré), sans dépendre du listing.
"""
import sys
import requests

CHECKSUM_URL = (
    "https://data.binance.vision/data/spot/monthly/klines/"
    "BTCUSDT/1d/BTCUSDT-1d-2020-01.zip.CHECKSUM"
)


def main():
    try:
        resp = requests.get(CHECKSUM_URL, timeout=15)
    except Exception as e:
        print(f"[ECHEC] Erreur réseau vers data.binance.vision : {e}")
        sys.exit(1)

    if resp.status_code != 200:
        print(f"[ECHEC] Statut HTTP {resp.status_code} pour {CHECKSUM_URL}")
        sys.exit(1)

    text = resp.text.strip()
    # Une ligne de checksum SHA256 ressemble à :
    # "<64 caractères hex>  BTCUSDT-1d-2020-01.zip"
    parts = text.split()
    if len(parts) < 2 or len(parts[0]) != 64:
        print(f"[ECHEC] Réponse inattendue (pas un CHECKSUM valide) : {text[:200]!r}")
        sys.exit(1)

    print(f"[OK] Binance public data accessible : fichier de référence vérifié ({parts[1]})")


if __name__ == "__main__":
    main()
