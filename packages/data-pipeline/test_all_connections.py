"""
Lance tous les scripts de test de connexion et affiche un résumé.
Usage : python packages/data-pipeline/test_all_connections.py
"""
import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    "test_connection_yfinance.py",
    "test_connection_binance.py",
    "test_connection_alphavantage.py",
    "test_connection_twelvedata.py",
    "test_connection_fred.py",
    "test_connection_stooq.py",
    "test_connection_secedgar.py",
]

HERE = Path(__file__).parent


def main():
    results = {}
    for script in SCRIPTS:
        path = HERE / script
        print(f"\n--- {script} ---")
        proc = subprocess.run([sys.executable, str(path)], capture_output=True, text=True)
        print(proc.stdout.strip())
        if proc.returncode != 0:
            print(proc.stderr.strip())
        results[script] = proc.returncode == 0

    print("\n=== Résumé ===")
    for script, ok in results.items():
        status = "OK" if ok else "ECHEC"
        print(f"  [{status}] {script}")

    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
