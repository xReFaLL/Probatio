"""
Sprint 7 — Orchestration côté process parent (appelé depuis apps/api/).

Écrit le code utilisateur, les données OHLCV et les paramètres dans un
répertoire temporaire dédié, lance sandbox/runner.py dans un subprocess
Python séparé (isolation process — pas de fork du process API), applique un
timeout mur en complément des limites CPU/mémoire posées par le runner
lui-même, puis parse le résultat.

C'est le seul point d'entrée que apps/api/custom_strategies.py doit
utiliser -- il ne doit jamais appeler sandbox/runner.py ou exécuter du code
utilisateur par un autre chemin.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from sandbox.ast_validator import validate_strategy_code

_SANDBOX_DIR = Path(__file__).resolve().parent
_RUNNER_PATH = _SANDBOX_DIR / "runner.py"

# Timeouts mur, en secondes -- complètent (ne remplacent pas) le RLIMIT_CPU
# posé dans runner.py : couvrent le cas d'un code qui bloque sans consommer
# de CPU (ex. boucle d'attente active mal écrite qui ferait quand même du
# CPU en réalité -- mais on garde une marge de sécurité "temps mur" distincte
# du "temps CPU" par prudence, les deux mécanismes se recoupent volontairement).
QUICK_TEST_TIMEOUT_SECONDS = 15
FULL_RUN_TIMEOUT_SECONDS = 60

# Nombre de barres utilisées pour le test rapide (Sprint 7 -- "test rapide
# sur échantillon réduit de données avant lancement d'un backtest complet").
QUICK_TEST_SAMPLE_BARS = 250


@dataclass
class SandboxExecutionResult:
    status: str  # "ok" | "invalid" | "error" | "timeout"
    positions: list[int] = field(default_factory=list)
    timestamps: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)  # erreurs de validation AST
    error: str | None = None  # message d'erreur d'exécution
    traceback: str | None = None
    stdout: str = ""
    stderr: str = ""
    execution_time_ms: int = 0


def _run_in_subprocess(
    source: str, df: pd.DataFrame, params: dict, mode: str, timeout_seconds: int,
) -> SandboxExecutionResult:
    started = time.monotonic()

    # Défense en profondeur : on valide ici aussi, avant même d'écrire quoi
    # que ce soit sur disque -- évite d'aller jusqu'au subprocess pour du
    # code qu'on sait déjà invalide, et donne un retour plus rapide côté API.
    required_function = "generate_signals" if mode == "vectorized" else "on_bar"
    pre_validation = validate_strategy_code(source, required_function)
    if not pre_validation.valid:
        return SandboxExecutionResult(status="invalid", errors=pre_validation.errors)

    with tempfile.TemporaryDirectory(prefix="probatio-sandbox-") as tmp:
        tmp_dir = Path(tmp)
        code_path = tmp_dir / "strategy_code.py"
        data_path = tmp_dir / "data.pkl"
        params_path = tmp_dir / "params.json"
        result_path = tmp_dir / "result.json"

        code_path.write_text(source, encoding="utf-8")
        # Pickle plutôt que Parquet ici : évite une dépendance supplémentaire
        # (pyarrow/fastparquet, absents de requirements.txt -- le Parquet de
        # l'entrepôt est lu via DuckDB, pas via pandas.to_parquet). Le fichier
        # est écrit par du code de confiance (ce process) et seulement relu
        # par runner.py juste après -- aucune désérialisation de données
        # provenant de l'utilisateur, donc pas de risque lié à pickle ici.
        df.to_pickle(data_path)
        params_path.write_text(json.dumps(params), encoding="utf-8")

        # Environnement minimal -- pas de variables héritées du process API
        # (clés API, chemins internes, etc.) qui n'ont rien à faire visibles
        # depuis du code utilisateur, même si celui-ci ne peut de toute façon
        # pas faire d'appel réseau (imports bloqués côté runner.py).
        minimal_env = {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}

        try:
            proc = subprocess.run(
                [sys.executable, str(_RUNNER_PATH), str(code_path), str(data_path),
                 str(params_path), mode, str(result_path)],
                cwd=str(tmp_dir),
                env=minimal_env,
                timeout=timeout_seconds,
                capture_output=True,
                text=True,
            )
        except subprocess.TimeoutExpired as e:
            return SandboxExecutionResult(
                status="timeout",
                error=f"Dépassement du temps limite ({timeout_seconds}s).",
                stdout=(e.stdout or "")[:2000] if isinstance(e.stdout, str) else "",
                stderr=(e.stderr or "")[:2000] if isinstance(e.stderr, str) else "",
                execution_time_ms=int((time.monotonic() - started) * 1000),
            )

        execution_time_ms = int((time.monotonic() - started) * 1000)
        stdout = (proc.stdout or "")[:2000]
        stderr = (proc.stderr or "")[:2000]

        if not result_path.exists():
            return SandboxExecutionResult(
                status="error",
                error="Le sandbox ne s'est pas terminé proprement (aucun résultat produit). "
                      "Voir stderr pour le détail.",
                stdout=stdout, stderr=stderr, execution_time_ms=execution_time_ms,
            )

        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            return SandboxExecutionResult(
                status="error", error=f"Résultat du sandbox illisible : {e}",
                stdout=stdout, stderr=stderr, execution_time_ms=execution_time_ms,
            )

        return SandboxExecutionResult(
            status=payload.get("status", "error"),
            positions=payload.get("positions", []),
            timestamps=payload.get("timestamps", []),
            errors=payload.get("errors", []),
            error=payload.get("error"),
            traceback=payload.get("traceback"),
            stdout=stdout, stderr=stderr, execution_time_ms=execution_time_ms,
        )


def quick_test(source: str, df: pd.DataFrame, params: dict, mode: str) -> SandboxExecutionResult:
    """
    Exécute la stratégie sur un échantillon réduit (dernières
    QUICK_TEST_SAMPLE_BARS barres) pour un retour rapide sur les erreurs de
    code, avant de lancer un backtest complet potentiellement long.
    """
    sample = df.tail(QUICK_TEST_SAMPLE_BARS).reset_index(drop=True)
    return _run_in_subprocess(source, sample, params, mode, QUICK_TEST_TIMEOUT_SECONDS)


def run_full(source: str, df: pd.DataFrame, params: dict, mode: str) -> SandboxExecutionResult:
    """Exécute la stratégie sur l'historique complet fourni (backtest réel)."""
    return _run_in_subprocess(source, df, params, mode, FULL_RUN_TIMEOUT_SECONDS)