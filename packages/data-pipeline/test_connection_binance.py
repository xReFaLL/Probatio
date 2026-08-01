"""
Test de connexion — Binance public data (data.binance.vision), pas de clé requise.

Correction (retour Sprint 0) : data.binance.vision est un bucket S3 statique.
Il n'y a PAS de "directory listing" HTML classique sur
/data/spot/daily/klines/BTCUSDT/1d/ (404 garanti) — il faut interroger
l'endpoint de listing S3 avec ?prefix=... qui renvoie du XML.
"""
import sys
import requests
import xml.etree.ElementTree as ET

LIST_URL = "https://data.binance.vision/?prefix=data/spot/daily/klines/BTCUSDT/1d/"


def main():
    try:
        resp = requests.get(LIST_URL, timeout=15)
    except Exception as e:
        print(f"[ECHEC] Erreur réseau vers data.binance.vision : {e}")
        sys.exit(1)

    if resp.status_code != 200:
        print(f"[ECHEC] Statut HTTP {resp.status_code} pour {LIST_URL}")
        sys.exit(1)

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        print(f"[ECHEC] Réponse non-XML inattendue : {e}")
        sys.exit(1)

    # Le XML S3 utilise un namespace ; on cherche les clés <Key> quel qu'il soit.
    keys = [el.text for el in root.iter() if el.tag.endswith("Key")]

    if not keys:
        print("[ECHEC] Aucune clé trouvée dans la réponse S3 (prefix incorrect ?)")
        sys.exit(1)

    print(f"[OK] Binance public data accessible : {len(keys)} fichiers listés pour BTCUSDT/1d")
    print(f"     Exemple : {keys[0]}")


if __name__ == "__main__":
    main()
