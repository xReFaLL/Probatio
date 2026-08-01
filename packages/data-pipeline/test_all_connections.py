"""
Lance tous les scripts de test de connexion et affiche un résumé.
Usage : python packages/data-pipeline/test_all_connections.py

Mise à jour (Sprint 3) : Stooq est passé en source OPTIONNELLE. Elle bloque
désormais les clients HTTP non-navigateur via un challenge anti-bot (voir
docs/data-sources.md) ; ce n'est plus une source de vérification croisée
fiable pour un pipeline automatisé, donc son échec ne doit plus faire
échouer toute la suite. Le script reste dans la liste pour visibilité (utile
si Stooq assouplit un jour sa protection), mais la vérification croisée
daily du pipeline utilise désormais Twelve Data
(voir verify_cross_check_twelvedata.py).
"""
import subprocess
import sys
from pathlib import Path

REQUIRED_SCRIPTS = [
    "test_connection_yfinance.py",
    "test_connection_binance.py",
    "test_connection_alphavantage.py",
    "test_connection_twelvedata.py",
    "test_connection_fred.py",
    "test_connection_secedgar.py",
]

OPTIONAL_SCRIPTS = [
    "test_connection_stooq.py",
]

HERE = Path(__file__).parent


def run_script(script: str) -> bool:
    path = HERE / script
    print(f"\n--- {script} ---")
    proc = subprocess.run([sys.executable, str(path)], capture_output=True, text=True)
    print(proc.stdout.strip())
    if proc.returncode != 0:
        print(proc.stderr.strip())
    return proc.returncode == 0


def main():
    results = {}
    for script in REQUIRED_SCRIPTS:
        results[script] = run_script(script)

    optional_results = {}
    for script in OPTIONAL_SCRIPTS:
        optional_results[script] = run_script(script)

    print("\n=== Résumé ===")
    for script, ok in results.items():
        print(f"  [{'OK' if ok else 'ECHEC'}] {script}")
    for script, ok in optional_results.items():
        label = "OK" if ok else "ECHEC (optionnel)"
        print(f"  [{label}] {script}")

    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
