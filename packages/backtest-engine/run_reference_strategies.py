"""
Sprint 4 — Validation du moteur de backtest vectorisé.

Lance les 2 stratégies de référence (croisement de moyennes mobiles, RSI)
sur un petit échantillon de symboles déjà présents dans l'entrepôt, affiche
les métriques de performance. Sert à vérifier que le moteur, les indicateurs
et les métriques fonctionnent correctement de bout en bout, avant de les
brancher sur l'API au Sprint 5.

Usage :
    python packages/backtest-engine/run_reference_strategies.py
"""
from warehouse_reader import load_ohlcv
from strategies import sma_crossover, rsi_mean_reversion
from engine_vectorized import run_backtest
from metrics import compute_metrics

# Un échantillon volontairement réduit et varié (actions US, action CAC 40,
# crypto) — pas besoin de scanner tout l'univers pour valider le moteur.
SAMPLE = [
    ("AAPL", "equity"),
    ("MC.PA", "equity"),
    ("BTCUSDT", "crypto"),
]

STRATEGIES = {
    "SMA crossover (20/50)": lambda df: sma_crossover(df, fast=20, slow=50),
    "RSI mean-reversion (14, 30/70)": lambda df: rsi_mean_reversion(
        df, length=14, oversold=30, overbought=70
    ),
}

INITIAL_CAPITAL = 10_000.0
COMMISSION = 0.0005
SLIPPAGE = 0.0005


def main():
    for symbol, asset_class in SAMPLE:
        print(f"\n{'=' * 60}")
        print(f"{symbol} ({asset_class})")
        print("=" * 60)
        try:
            df = load_ohlcv(symbol, asset_class)
        except FileNotFoundError as e:
            print(f"  [IGNORÉ] {e}")
            continue

        print(f"  {len(df)} barres, du {df['timestamp'].min()} au {df['timestamp'].max()}")

        for name, strategy_fn in STRATEGIES.items():
            positions = strategy_fn(df)
            result = run_backtest(
                df, positions,
                initial_capital=INITIAL_CAPITAL,
                commission=COMMISSION,
                slippage=SLIPPAGE,
            )
            m = compute_metrics(result["equity_curve"], result["trades"], INITIAL_CAPITAL)

            print(f"\n  --- {name} ---")
            print(f"    Capital final     : {m['final_equity']:>12,.2f}  (départ {INITIAL_CAPITAL:,.2f})")
            print(f"    Rendement total   : {(m['final_equity'] / INITIAL_CAPITAL - 1):>12.1%}")
            print(f"    Sharpe            : {m['sharpe']:>12.2f}")
            print(f"    Sortino           : {m['sortino']:>12.2f}")
            print(f"    Max drawdown      : {m['max_drawdown']:>12.1%}")
            print(f"    Win rate          : {m['win_rate']:>12.1%}")
            print(f"    Profit factor     : {m['profit_factor']:>12.2f}")
            print(f"    Nombre de trades  : {m['total_trades']:>12}")

    print(f"\n{'=' * 60}")
    print("Terminé. Si tu vois des métriques cohérentes ci-dessus (pas de")
    print("NaN, pas d'erreur), le moteur fonctionne de bout en bout.")


if __name__ == "__main__":
    main()