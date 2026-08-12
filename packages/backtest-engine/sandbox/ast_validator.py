"""
Sprint 7 — Validation statique du code de stratégie custom (whitelist AST).

Première ligne de défense, appliquée AVANT toute exécution (même dans le
subprocess isolé) : on parse le code soumis et on rejette tout nœud AST qui
ne fait pas partie d'une liste explicite d'autorisations. Volontairement
restrictif — un faux positif (code légitime rejeté) est un problème mineur
(l'utilisateur adapte son code), un faux négatif (code dangereux accepté)
ne l'est pas.

Ce module ne s'exécute jamais dans le subprocess : il tourne côté process
API (executor.py l'appelle avant de lancer quoi que ce soit), donc pas
besoin qu'il soit lui-même sandboxé.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field

# Modules dont l'import est autorisé dans le code utilisateur. Volontairement
# limité à ce qui est nécessaire pour écrire une stratégie (cf. brief :
# "imports autorisés limités à pandas/numpy/pandas-ta-classic").
ALLOWED_IMPORT_MODULES = {"pandas", "numpy", "pandas_ta_classic"}

# Fonctions/noms interdits même sans import explicite (accessibles via
# builtins). eval/exec/compile/__import__ permettent de contourner le reste
# du filtre ; open/input font de l'I/O ; globals/locals/vars/breakpoint
# donnent un accès d'introspection qui facilite l'évasion de sandbox.
FORBIDDEN_NAMES = {
    "eval", "exec", "compile", "__import__", "open", "input",
    "globals", "locals", "vars", "breakpoint", "exit", "quit", "help",
    "memoryview", "getattr", "setattr", "delattr",
}

# Attributs interdits : tout ce qui commence ET finit par "__" (dunder) est
# la voie classique pour remonter jusqu'à des objets dangereux depuis un
# objet a priori inoffensif (ex. ().__class__.__bases__[0].__subclasses__()).
def _is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


# Nœuds AST catégoriquement interdits, quel que soit le contexte.
FORBIDDEN_NODE_TYPES = (
    ast.Global,
    ast.Nonlocal,
)


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)


def validate_strategy_code(source: str, required_function: str) -> ValidationResult:
    """
    Valide le code source d'une stratégie custom.

    required_function : "generate_signals" (mode vectorisé) ou "on_bar"
        (mode event-driven) — la fonction doit être définie au niveau module.

    Ne lève jamais d'exception pour du code utilisateur invalide : retourne
    toujours un ValidationResult, erreurs listées dans .errors. Une
    SyntaxError de parsing est elle-même convertie en erreur de validation.
    """
    errors: list[str] = []

    try:
        tree = ast.parse(source, mode="exec")
    except SyntaxError as e:
        return ValidationResult(valid=False, errors=[f"Erreur de syntaxe : {e}"])

    found_function = False

    for node in ast.walk(tree):
        # --- imports ---------------------------------------------------
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_level = alias.name.split(".")[0]
                if top_level not in ALLOWED_IMPORT_MODULES:
                    errors.append(
                        f"Import non autorisé : '{alias.name}' (ligne {node.lineno}). "
                        f"Modules autorisés : {', '.join(sorted(ALLOWED_IMPORT_MODULES))}."
                    )
        elif isinstance(node, ast.ImportFrom):
            top_level = (node.module or "").split(".")[0]
            if top_level not in ALLOWED_IMPORT_MODULES:
                errors.append(
                    f"Import non autorisé : 'from {node.module} import ...' "
                    f"(ligne {node.lineno}). Modules autorisés : "
                    f"{', '.join(sorted(ALLOWED_IMPORT_MODULES))}."
                )

        # --- noms interdits (appel direct d'une fonction dangereuse) ----
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_NAMES:
                errors.append(f"Nom interdit : '{node.id}' (ligne {node.lineno}).")

        # --- attributs dunder --------------------------------------------
        elif isinstance(node, ast.Attribute):
            if _is_dunder(node.attr):
                errors.append(
                    f"Accès à un attribut réservé interdit : '.{node.attr}' "
                    f"(ligne {node.lineno})."
                )

        elif isinstance(node, FORBIDDEN_NODE_TYPES):
            errors.append(f"Instruction interdite : {type(node).__name__} (ligne {node.lineno}).")

        # --- fonction requise présente ? --------------------------------
        elif isinstance(node, ast.FunctionDef) and node.name == required_function:
            found_function = True

    if not found_function:
        errors.append(
            f"Fonction requise absente : le code doit définir `def {required_function}(...)` "
            f"au niveau module."
        )

    return ValidationResult(valid=not errors, errors=errors)