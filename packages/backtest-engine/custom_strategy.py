"""
Sprint 7 — Adapte le résultat du sandbox (sandbox/executor.py) au même
contrat que les stratégies internes (strategies.sma_crossover,
strategies.rsi_mean_reversion) : une pandas.Series de positions désirées
({-1, 0, 1}) alignée sur le DataFrame OHLCV d'entrée.

C'est le seul fichier qui fait le pont entre le sandbox et
engine_vectorized.py / engine_event_driven.py -- ceux-ci restent inchangés
et continuent d'ignorer totalement l'existence de code utilisateur : ils ne
voient jamais qu'une Series de positions, qu'elle vienne d'une stratégie
interne ou d'une stratégie custom.
"""
from __future__ import annotations

import pandas as pd

from sandbox.executor import SandboxExecutionResult, quick_test, run_full


class CustomStrategyError(Exception):
    """Levée quand le sandbox ne produit pas un résultat exploitable (code
    invalide, erreur d'exécution, timeout). Le message est destiné à être
    renvoyé tel quel à l'utilisateur (voir apps/api/custom_strategies.py)."""

    def __init__(self, sandbox_result: SandboxExecutionResult):
        self.sandbox_result = sandbox_result
        super().__init__(_format_error(sandbox_result))


def _format_error(result: SandboxExecutionResult) -> str:
    if result.status == "invalid":
        return "Code invalide : " + " ; ".join(result.errors)
    if result.status == "timeout":
        return result.error or "Dépassement du temps limite d'exécution."
    return result.error or "Erreur inconnue lors de l'exécution du sandbox."


def _positions_to_series(result: SandboxExecutionResult, df: pd.DataFrame) -> pd.Series:
    positions = pd.Series(result.positions, index=df.index[: len(result.positions)], dtype="int64")
    return positions.reindex(df.index).fillna(0).astype(int)


def generate_signals_sandboxed(
    df: pd.DataFrame, params: dict, source: str, mode: str = "vectorized",
) -> pd.Series:
    """
    Équivalent sandboxé de strategies.sma_crossover / rsi_mean_reversion :
    même signature de sortie (Series alignée sur df), mais le calcul se fait
    dans sandbox/runner.py via un subprocess isolé plutôt qu'en appelant
    directement une fonction Python de confiance.

    Lève CustomStrategyError si le code est invalide ou plante -- à charge
    de l'appelant (apps/api/custom_strategies.py) de traduire ça en réponse
    HTTP appropriée plutôt que de laisser remonter une 500 générique.
    """
    result = run_full(source, df, params, mode)
    if result.status != "ok":
        raise CustomStrategyError(result)
    return _positions_to_series(result, df)


def quick_test_sandboxed(
    df: pd.DataFrame, params: dict, source: str, mode: str = "vectorized",
) -> SandboxExecutionResult:
    """
    Test rapide sur échantillon réduit (voir sandbox.executor.quick_test) --
    retourne le SandboxExecutionResult brut (pas de conversion en Series ni
    d'exception levée) : ce endpoint est fait pour donner un retour détaillé
    à l'utilisateur pendant qu'il écrit son code, succès ou échec.
    """
    return quick_test(source, df, params, mode)