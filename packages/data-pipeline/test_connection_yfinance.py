"""
Test de connexion — yfinance (Yahoo Finance, pas de clé requise).
Vérifie qu'on peut récupérer un historique daily minimal pour un ticker connu.
"""
import sys

def main():
    try:
        import yfinance as yf
    except ImportError:
        print("[ECHEC] Le package 'yfinance' n'est pas installé (pip install -r requirements.txt)")
        sys.exit(1)

    ticker = "AAPL"
    try:
        data = yf.download(ticker, period="5d", interval="1d", progress=False)
    except Exception as e:
        print(f"[ECHEC] Erreur lors de l'appel yfinance : {e}")
        sys.exit(1)

    if data is None or data.empty:
        print(f"[ECHEC] Aucune donnée retournée pour {ticker}. yfinance peut être temporairement throttle.")
        sys.exit(1)

    print(f"[OK] yfinance : {len(data)} lignes récupérées pour {ticker}")
    print(data.tail(2))


if __name__ == "__main__":
    main()
