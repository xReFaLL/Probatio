"""
Sprint 7 — Point d'entrée exécuté DANS le subprocess isolé.

Lancé par executor.py via `python3 -m sandbox.runner <code> <data> <params>
<mode> <result>` (ou en script direct — voir `if __name__ == "__main__"` en
bas de fichier). Ne jamais importer ce module dans le process API principal
pour exécuter du code utilisateur directement : toute la protection repose
sur le fait que ce fichier tourne dans un process séparé, avec ses propres
limites de ressources.

Ordre des opérations volontairement figé :
  1. Poser les limites de ressources AVANT tout le reste (y compris avant
     l'import de pandas/numpy) — si le process dépasse la limite mémoire
     pendant ses propres imports, mieux vaut qu'il crashe tout de suite.
  2. Imports réels (pandas/numpy/pandas_ta_classic) faits ici, en dehors de
     toute restriction — ce sont des imports du projet, pas du code
     utilisateur.
  3. Re-validation AST du code utilisateur (défense en profondeur : le code
     a déjà été validé côté process API par ast_validator.py avant d'écrire
     le fichier temporaire, mais on ne fait jamais confiance à un fichier
     qu'on n'a pas soi-même généré dans la même passe).
  4. Exécution du code utilisateur avec des builtins restreints et sans
     capacité d'import supplémentaire (les seuls modules disponibles sont
     ceux injectés explicitement dans son espace de noms : pd, np, ta).
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

# --- 1. Limites de ressources, avant tout le reste --------------------------
# POSIX uniquement (le module `resource` n'existe pas sous Windows — ce
# projet cible un déploiement Docker/Linux, cf. docker-compose.yml, donc pas
# de fallback nécessaire ; à l'exécution locale hors Docker sous Windows,
# cette limite ne s'applique simplement pas, le timeout mur du subprocess
# parent (executor.py) reste la protection de dernier recours dans ce cas).
def _apply_resource_limits() -> None:
    try:
        import resource
    except ImportError:
        return  # Windows -- pas de limites POSIX, le timeout mur suffit en secours.

    # CPU : coupe le process s'il consomme plus de N secondes CPU, quel que
    # soit le temps mur écoulé (boucle infinie pure CPU, ex. `while True: pass`).
    cpu_seconds = 10
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))

    # Mémoire virtuelle : évite qu'une allocation malveillante ou accidentelle
    # (ex. `[0] * 10**15`) n'épuise la mémoire de la machine hôte.
    memory_bytes = 512 * 1024 * 1024  # 512 Mo
    try:
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    except (ValueError, OSError):
        pass  # certains environnements (ex. macOS) refusent RLIMIT_AS -- best effort.

    # Taille de fichier plafonnée plutôt qu'interdite à zéro : le runner
    # lui-même doit pouvoir écrire son fichier de résultat (result.json,
    # positions sérialisées) en fin d'exécution. Le code utilisateur, lui,
    # n'a de toute façon aucun moyen d'écrire un fichier : open() est retiré
    # des builtins restreints plus bas. 10 Mo couvre largement même un
    # historique complet (des dizaines de milliers de barres, un entier par
    # barre) tout en bornant une éventuelle sortie anormalement volumineuse.
    ten_mb = 10 * 1024 * 1024
    try:
        resource.setrlimit(resource.RLIMIT_FSIZE, (ten_mb, ten_mb))
    except (ValueError, OSError):
        pass

    # Pas de core dumps (pourraient exposer des données en cas de crash).
    try:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except (ValueError, OSError):
        pass


_apply_resource_limits()

# --- 2. Imports réels du projet (pas du code utilisateur) -------------------
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

try:
    import pandas_ta_classic as ta  # noqa: E402
except ImportError:
    ta = None  # la stratégie utilisateur peut ne pas en avoir besoin

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sandbox.ast_validator import validate_strategy_code  # noqa: E402

MAX_STDOUT_CHARS = 8000  # évite qu'un print() en boucle ne sature les logs


# --- 4. Builtins restreints ---------------------------------------------------
_SAFE_BUILTIN_NAMES = (
    "abs", "all", "any", "bool", "dict", "enumerate", "filter", "float",
    "int", "isinstance", "issubclass", "len", "list", "map", "max", "min",
    "next", "print", "range", "reversed", "round", "set", "slice", "sorted",
    "str", "sum", "tuple", "type", "zip",
    "True", "False", "None",
    "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
    "RuntimeError", "StopIteration", "ZeroDivisionError", "ArithmeticError",
    "AttributeError", "NotImplementedError",
)


def _blocked_import(name, *args, **kwargs):
    raise ImportError(
        f"Import de '{name}' interdit dans le sandbox. Modules disponibles : "
        f"pd, np, ta (déjà injectés, pas besoin de les importer)."
    )


def _build_restricted_globals(user_source: str) -> dict:
    real_builtins = __builtins__ if isinstance(__builtins__, dict) else vars(__builtins__)
    safe_builtins = {name: real_builtins[name] for name in _SAFE_BUILTIN_NAMES if name in real_builtins}
    safe_builtins["__import__"] = _blocked_import

    restricted_globals = {
        "__builtins__": safe_builtins,
        "__name__": "user_strategy",
        "pd": pd,
        "pandas": pd,
        "np": np,
        "numpy": np,
        "ta": ta,
        "pandas_ta_classic": ta,
    }
    return restricted_globals


class Context:
    """
    Contexte passé à on_bar(context, bar) en mode event-driven.

    Expose uniquement une vue en lecture sur l'historique disponible JUSQU'À
    la barre courante incluse (pas d'anticipation possible) et un espace de
    stockage libre (`state`) pour que la stratégie garde son propre état
    d'une barre à l'autre (ex. compteurs, dernière valeur de croisement...).
    """

    __slots__ = ("history", "index", "state")

    def __init__(self, history: pd.DataFrame, index: int, state: dict):
        self.history = history
        self.index = index
        self.state = state


def _run_vectorized(user_globals: dict, df: pd.DataFrame, params: dict) -> list:
    fn = user_globals.get("generate_signals")
    if fn is None or not callable(fn):
        raise RuntimeError("La fonction generate_signals(df, params) est introuvable.")

    result = fn(df, params)

    if not isinstance(result, pd.Series):
        raise RuntimeError(
            f"generate_signals doit retourner une pandas.Series, reçu : {type(result).__name__}."
        )
    if len(result) != len(df):
        raise RuntimeError(
            f"generate_signals doit retourner une Series de même longueur que df "
            f"({len(df)} lignes attendues, {len(result)} reçues)."
        )

    positions = result.reindex(df.index).fillna(0)
    positions = positions.clip(lower=-1, upper=1).round().astype(int)
    return positions.tolist()


def _run_event_driven(user_globals: dict, df: pd.DataFrame, params: dict) -> list:
    fn = user_globals.get("on_bar")
    if fn is None or not callable(fn):
        raise RuntimeError("La fonction on_bar(context, bar) est introuvable.")

    state: dict = {}
    positions: list[int] = []
    for i in range(len(df)):
        history = df.iloc[: i + 1]
        bar = df.iloc[i]
        context = Context(history=history, index=i, state=state)
        desired = fn(context, bar)
        if desired is None:
            desired = 0
        try:
            desired = int(desired)
        except (TypeError, ValueError):
            raise RuntimeError(
                f"on_bar doit retourner un entier dans {{-1, 0, 1}} (barre {i}), "
                f"reçu : {desired!r}."
            )
        desired = max(-1, min(1, desired))
        positions.append(desired)
    return positions


def main() -> int:
    if len(sys.argv) != 6:
        print("Usage: runner.py <code_path> <data_path> <params_path> <mode> <result_path>", file=sys.stderr)
        return 2

    code_path, data_path, params_path, mode, result_path = sys.argv[1:6]
    result: dict = {"status": "error", "error": "Résultat non produit (bug interne du runner)."}

    try:
        user_source = Path(code_path).read_text(encoding="utf-8")

        required_function = "generate_signals" if mode == "vectorized" else "on_bar"
        validation = validate_strategy_code(user_source, required_function)
        if not validation.valid:
            result = {"status": "invalid", "errors": validation.errors}
            Path(result_path).write_text(json.dumps(result), encoding="utf-8")
            return 1

        df = pd.read_pickle(data_path)  # écrit par executor.py (code de confiance) -- voir commentaire là-bas
        params = json.loads(Path(params_path).read_text(encoding="utf-8"))

        user_globals = _build_restricted_globals(user_source)
        code_obj = compile(user_source, filename="<user_strategy>", mode="exec")
        exec(code_obj, user_globals)  # noqa: S102 -- namespace restreint construit ci-dessus

        if mode == "vectorized":
            positions = _run_vectorized(user_globals, df, params)
        elif mode == "event_driven":
            positions = _run_event_driven(user_globals, df, params)
        else:
            raise RuntimeError(f"Mode inconnu : {mode!r} (attendu 'vectorized' ou 'event_driven').")

        result = {
            "status": "ok",
            "positions": positions,
            "timestamps": [str(ts) for ts in df["timestamp"].tolist()],
        }

    except Exception as exc:  # noqa: BLE001 -- on veut TOUJOURS renvoyer un résultat structuré
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        result = {"status": "error", "error": str(exc), "traceback": tb[-4000:]}

    finally:
        try:
            Path(result_path).write_text(json.dumps(result), encoding="utf-8")
        except Exception:  # noqa: BLE001 -- dernier recours, on tente stderr
            print(json.dumps(result), file=sys.stderr)

    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())