"""
Sprint 7 — Sandbox d'exécution pour les stratégies custom utilisateur.

Ce sous-package isole tout le code lié à l'exécution de code Python soumis
par l'utilisateur (voir apps/api/custom_strategies.py pour les endpoints qui
l'utilisent). Trois responsabilités séparées :

  - ast_validator.py  : validation statique (whitelist AST) — première ligne
                        de défense, avant toute exécution.
  - runner.py         : point d'entrée exécuté DANS le subprocess isolé —
                        pose ses propres limites de ressources, restreint les
                        builtins et les imports, exécute le code utilisateur,
                        écrit le résultat en JSON sur stdout.
  - executor.py       : orchestration côté process parent (API) — écrit les
                        fichiers temporaires, lance le subprocess, applique
                        le timeout mur, parse le résultat.

Principe de conception (voir résumé de sprint pour le détail) : le code
utilisateur, même dans le sandbox, ne fait jamais que calculer une position
désirée (Series alignée sur les barres). Il ne touche jamais au cash, aux
ordres, au sizing ou aux commissions — cette simulation reste entièrement
dans engine_vectorized.py / engine_event_driven.py, du code de confiance,
déjà en place et testé depuis les Sprints 4 et 6. Le sandbox ne fait donc
jamais "plus" que produire des signaux : la surface d'attaque utile d'un
bug de sandboxing est ainsi limitée à de la fuite d'info / déni de service
sur la machine hôte, jamais à une falsification des résultats de backtest
d'autrui (mono-utilisateur MVP, mais un principe qui vieillit bien).
"""