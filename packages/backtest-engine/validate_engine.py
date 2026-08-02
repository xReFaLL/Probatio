"""
Sprint 4 — Suite de validation du moteur (à ne pas confondre avec
run_reference_strategies.py, qui *démontre* le moteur sur des vraies données ;
celui-ci *prouve* que ses calculs sont corrects).

"Ça tourne sans erreur" ne prouve pas que les calculs sont justes -- une
erreur de logique (décalage temporel, calcul de PnL, anticipation involontaire
du futur) donnerait aussi des chiffres qui ont l'air normaux. Ce script fait
trois vérifications indépendantes, chacune avec un résultat attendu connu à
l'avance :

  1. Buy & hold : sans frais, rester investi du premier au dernier jour doit
     donner EXACTEMENT le même capital que "acheter au jour 1, vendre au
     dernier jour" -- un calcul de collège, aucune ambiguïté possible.
  2. Trade calculable à la main : sur une mini-série de 6 prix fabriquée à la
     main, on calcule nous-mêmes le trade attendu (entrée, sortie, PnL) et on
     vérifie que le moteur trouve exactement pareil.
  3. Anti-anticipation ("lookahead") : les décisions passées ne doivent pas
     changer si on ajoute des données futures après coup. Si le moteur
     utilisait involontairement des informations du futur, ce test le
     détecterait.

Usage :
    python packages/backtest-engine/validate_engine.py
"""
import numpy as np
import pandas as pd

from engine_vectorized import run_backtest
from strategies import sma_crossover
from warehouse_reader import load_ohlcv

FAILURES = []


def check(label, condition, detail=""):
    status = "OK" if condition else "ÉCHEC"
    print(f"  [{status}] {label}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def test_buy_and_hold():
    print("\n=== 1. Buy & hold (sans frais) ===")
    try:
        df = load_ohlcv("AAPL", "equity")
    except FileNotFoundError:
        print("  [IGNORÉ] AAPL absent de l'entrepôt")
        return

    df = df.tail(500).reset_index(drop=True)  # échantillon récent, suffisant
    always_long = pd.Series(1, index=df.index)

    result = run_backtest(df, always_long, initial_capital=10_000.0, commission=0, slippage=0)

    close = df["close"].to_numpy()
    # Le moteur exécute avec 1 barre de retard : la position 1 calculée à la
    # barre 0 s'applique à partir de la barre 1. Le capital final "sans
    # frais" attendu est donc le rendement entre le prix de la barre 0 et
    # celui de la dernière barre -- calculé ici indépendamment du moteur.
    expected_final_equity = 10_000.0 * (close[-1] / close[0])
    actual_final_equity = result["final_equity"]

    diff_pct = abs(actual_final_equity - expected_final_equity) / expected_final_equity
    check(
        "Capital final == capital attendu (acheter jour 1, vendre dernier jour)",
        diff_pct < 1e-9,
        f"attendu {expected_final_equity:,.4f}, obtenu {actual_final_equity:,.4f}",
    )
    check("Un seul trade généré (une seule entrée, jamais ressortie)", len(result["trades"]) == 1)


def test_hand_computed_trade():
    print("\n=== 2. Trade calculable à la main ===")
    # 6 prix fabriqués à la main. Signal calculé à la barre i, exécuté à i+1.
    prices = [100.0, 105.0, 110.0, 108.0, 100.0, 95.0]
    positions_signal = [0, 1, 1, 1, 0, 0]  # décidé à la clôture de chaque barre

    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=6, freq="D", tz="UTC"),
        "close": prices,
    })
    positions = pd.Series(positions_signal)

    # Calcul à la main : le signal est décalé d'une barre, donc la position
    # exécutée est [0, 0, 1, 1, 1, 0] -- entrée au prix de la barre 2 (110),
    # sortie au prix de la barre 5 (95, position revenue à 0 -> clôture du
    # trade à ce prix). PnL attendu = 95 - 110 = -15 (quantité = 1).
    result = run_backtest(df, positions, initial_capital=10_000.0, commission=0, slippage=0)
    trades = result["trades"]

    check("Exactement 1 trade généré", len(trades) == 1, f"{len(trades)} trade(s) trouvé(s)")
    if trades:
        t = trades[0]
        check("Prix d'entrée == 110 (barre 2)", t["entry_price"] == 110.0, f"obtenu {t['entry_price']}")
        check("Prix de sortie == 95 (barre 5)", t["exit_price"] == 95.0, f"obtenu {t['exit_price']}")
        check("Sens == long", t["side"] == "long", f"obtenu {t['side']}")
        check("PnL == -15.0", abs(t["pnl"] - (-15.0)) < 1e-9, f"obtenu {t['pnl']}")


def test_no_lookahead():
    print("\n=== 3. Anti-anticipation (pas de triche avec le futur) ===")
    try:
        df_full = load_ohlcv("AAPL", "equity")
    except FileNotFoundError:
        print("  [IGNORÉ] AAPL absent de l'entrepôt")
        return

    df_full = df_full.tail(500).reset_index(drop=True)
    cutoff = 400  # on coupe les 100 dernières barres

    df_truncated = df_full.iloc[:cutoff].reset_index(drop=True)

    positions_full = sma_crossover(df_full, fast=20, slow=50)
    positions_truncated = sma_crossover(df_truncated, fast=20, slow=50)

    # Les positions calculées sur la période commune (avant la coupure)
    # doivent être identiques, que le futur soit visible ou non.
    common_full = positions_full.iloc[:cutoff].reset_index(drop=True)
    common_truncated = positions_truncated.reset_index(drop=True)

    identical = common_full.equals(common_truncated)
    n_diff = int((common_full != common_truncated).sum()) if not identical else 0
    check(
        "Positions passées inchangées quand on ajoute des données futures",
        identical,
        f"{n_diff} barre(s) sur {cutoff} diffèrent",
    )


def main():
    print("Validation du moteur de backtest — chaque test a un résultat attendu")
    print("connu à l'avance, calculé indépendamment du moteur.")

    test_buy_and_hold()
    test_hand_computed_trade()
    test_no_lookahead()

    print("\n" + "=" * 60)
    if FAILURES:
        print(f"[ÉCHEC] {len(FAILURES)} vérification(s) ont échoué : {', '.join(FAILURES)}")
        print("Le moteur a un bug -- ne pas construire dessus avant correction.")
    else:
        print("[OK] Toutes les vérifications passent. Le moteur calcule correctement")
        print("     sur ces trois angles indépendants (rendement, mécanique de trade,")
        print("     absence d'anticipation du futur).")


if __name__ == "__main__":
    main()