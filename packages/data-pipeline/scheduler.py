"""
Ordonnancement automatique de l'ingestion (APScheduler) — remplace le
placeholder des sprints d'ingestion (Sprint 1-3).

Ce scheduler ne fait AUCUN appel réseau lui-même : il se contente de lancer,
à intervalles réguliers, les scripts d'ingestion existants
(ingest_yfinance.py, ingest_binance.py, ingest_fred.py, ingest_secedgar.py,
ingest_alphavantage.py) en sous-processus indépendants — chacun restant
l'unique point d'entrée réseau de sa source, comme documenté dans son propre
docstring. Le scheduler ajoute uniquement la couche « quand » ; le « quoi »
et le « comment » restent dans chaque script.

Deux groupes de fréquence, pilotés par .env (voir .env.example) :
  - INGEST_DAILY_CRON  (défaut "0 22 * * 1-5", jours ouvrés 22h) :
    yfinance, fred, secedgar, alphavantage — toutes les sources dont la
    fraîcheur se mesure à la journée (marchés actions/forex/commodities
    fermés, séries macro/fondamentaux publiées au mieux quotidiennement).
  - INGEST_CRYPTO_CRON (défaut "0 * * * *", toutes les heures) :
    binance — seule source dont le marché ne ferme jamais.

Un troisième job, optionnel et désactivable, exécute le bilan de santé de
l'entrepôt (check_warehouse_health.py) une fois par semaine à titre de
garde-fou silencieux — voir INGEST_HEALTHCHECK_CRON ci-dessous.
fix_null_ohlc_rows.py n'est volontairement PAS planifié : c'est un nettoyage
ponctuel pour un bug d'écriture déjà corrigé dans parquet_writer.py, pas une
tâche récurrente (voir son docstring).

Usage :
    python packages/data-pipeline/scheduler.py                   # démarre la boucle (bloquant)
    python packages/data-pipeline/scheduler.py --run-now daily   # lance le groupe "daily" une fois, puis quitte
    python packages/data-pipeline/scheduler.py --run-now crypto  # idem pour "crypto"
    python packages/data-pipeline/scheduler.py --run-now healthcheck
    python packages/data-pipeline/scheduler.py --run-now all     # les trois groupes, séquentiellement
    python packages/data-pipeline/scheduler.py --dry-run         # affiche juste les crons résolus et sort

En local (hors Docker), tourne comme un processus à part, en parallèle de
l'API :
    python packages/data-pipeline/scheduler.py &
"""
import argparse
import logging
import os
import signal
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("scheduler")
logging.getLogger("apscheduler").setLevel(logging.WARNING)

BASE_DIR = Path(__file__).resolve().parent

# Chaque script est lancé via `python <script>.py` en sous-processus, avec
# BASE_DIR comme cwd : Python place alors automatiquement ce dossier en tête
# de sys.path, ce qui satisfait les imports "flat" internes aux scripts
# (ex: `from universe import ...`) indépendamment du répertoire depuis lequel
# le scheduler lui-même est démarré.
SUBPROCESS_TIMEOUT = 6 * 3600  # 6h — garde-fou large ; un job qui dépasse ça est probablement bloqué

# Groupes de jobs : id -> (variable d'env du cron, cron par défaut, scripts à lancer dans l'ordre)
JOB_GROUPS = {
    "daily": {
        "cron_env": "INGEST_DAILY_CRON",
        "cron_default": "0 22 * * 1-5",
        "scripts": [
            "ingest_yfinance.py",      # actions, indices, forex, commodities
            "ingest_fred.py",          # macro
            "ingest_secedgar.py",      # fondamentaux US (SEC)
            "ingest_alphavantage.py",  # fondamentaux — cycle roulant (curseur), rate-limited
        ],
    },
    "crypto": {
        "cron_env": "INGEST_CRYPTO_CRON",
        "cron_default": "0 * * * *",
        "scripts": [
            "ingest_binance.py",
        ],
    },
    "healthcheck": {
        # Pas de variable dédiée dans .env.example à ce stade : job optionnel,
        # désactivable en mettant INGEST_HEALTHCHECK_CRON="" dans .env.
        "cron_env": "INGEST_HEALTHCHECK_CRON",
        "cron_default": "0 6 * * 0",  # dimanche 6h — n'entre en conflit avec aucun job d'ingestion
        "scripts": [
            "check_warehouse_health.py",
        ],
    },
}


def run_script(script_name: str) -> bool:
    """Lance un script d'ingestion en sous-processus et logue son issue.

    Retourne True si le script s'est terminé avec un code de sortie 0.
    N'échoue jamais bruyamment côté scheduler : une source en échec ne doit
    pas empêcher les autres scripts du même groupe de s'exécuter.
    """
    script_path = BASE_DIR / script_name
    if not script_path.exists():
        log.error("  -> introuvable : %s", script_path)
        return False

    log.info("  -> lancement de %s", script_name)
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(BASE_DIR),
            timeout=SUBPROCESS_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        log.error("  -> %s : timeout dépassé (%ds), processus tué", script_name, SUBPROCESS_TIMEOUT)
        return False
    except Exception as e:
        log.error("  -> %s : échec au lancement (%s)", script_name, e)
        return False

    if result.returncode == 0:
        log.info("  -> %s : OK", script_name)
        return True

    log.error("  -> %s : échec (code %d)", script_name, result.returncode)
    return False


def run_group(group_id: str) -> bool:
    """Exécute séquentiellement tous les scripts d'un groupe (daily/crypto/healthcheck).

    Séquentiel par choix, pas par contrainte technique : évite que plusieurs
    scripts écrivent dans data/app.db (SQLite) au même instant, et reste
    cohérent avec le fait qu'aucune de ces sources n'a de contrainte de
    latence à la minute près.
    """
    group = JOB_GROUPS[group_id]
    scripts = group["scripts"]
    log.info("=" * 60)
    log.info("Groupe '%s' — %d script(s)", group_id, len(scripts))

    ok, failed = [], []
    for script_name in scripts:
        if run_script(script_name):
            ok.append(script_name)
        else:
            failed.append(script_name)

    log.info("Groupe '%s' terminé — %d OK, %d échec(s)%s", group_id, len(ok), len(failed),
              f" ({', '.join(failed)})" if failed else "")
    return not failed


def resolve_cron(group_id: str) -> "str | None":
    """Lit le cron effectif d'un groupe depuis .env, ou son défaut.

    Une variable d'env explicitement vide ("") désactive le groupe — utile
    pour couper healthcheck (ou n'importe quel groupe) sans toucher au code.
    """
    group = JOB_GROUPS[group_id]
    raw = os.getenv(group["cron_env"])
    if raw is not None and raw.strip() == "":
        return None
    return (raw or group["cron_default"]).strip()


def build_scheduler() -> BlockingScheduler:
    scheduler = BlockingScheduler(timezone=os.getenv("SCHEDULER_TZ", "UTC"))

    for group_id, group in JOB_GROUPS.items():
        cron_expr = resolve_cron(group_id)
        if cron_expr is None:
            log.info("Groupe '%s' désactivé (%s=\"\")", group_id, group["cron_env"])
            continue

        try:
            trigger = CronTrigger.from_crontab(cron_expr, timezone=scheduler.timezone)
        except ValueError as e:
            log.error(
                "Cron invalide pour '%s' (%s=%r) : %s — groupe ignoré",
                group_id, group["cron_env"], cron_expr, e,
            )
            continue

        scheduler.add_job(
            run_group,
            trigger=trigger,
            args=[group_id],
            id=group_id,
            name=f"ingestion:{group_id}",
            max_instances=1,   # une exécution à la fois par groupe (pas de chevauchement si un run traîne)
            coalesce=True,     # après une coupure prolongée, ne rattrape pas les exécutions manquées une par une
            misfire_grace_time=3600,
        )
        log.info("Groupe '%s' planifié : %s (%s=%s)", group_id, cron_expr, group["cron_env"], cron_expr)

    return scheduler


def _log_job_event(event):
    if event.code == EVENT_JOB_ERROR:
        log.error("Job '%s' a levé une exception : %s", event.job_id, event.exception)
    else:
        job = event.job_id if hasattr(event, "job_id") else "?"
        log.debug("Job '%s' exécuté sans exception non gérée", job)


def main():
    parser = argparse.ArgumentParser(description="Ordonnancement de l'ingestion (APScheduler)")
    parser.add_argument(
        "--run-now",
        choices=["daily", "crypto", "healthcheck", "all"],
        default=None,
        help="Lance le(s) groupe(s) immédiatement (hors planification) puis quitte — pratique pour tester",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche les crons résolus (et les prochaines exécutions) sans démarrer la boucle",
    )
    args = parser.parse_args()

    if args.run_now:
        groups = list(JOB_GROUPS) if args.run_now == "all" else [args.run_now]
        overall_ok = True
        for group_id in groups:
            overall_ok = run_group(group_id) and overall_ok
        sys.exit(0 if overall_ok else 1)

    scheduler = build_scheduler()
    scheduler.add_listener(_log_job_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    if args.dry_run:
        log.info("--dry-run : prochaines exécutions planifiées —")
        for job in scheduler.get_jobs():
            log.info("  %s -> %s", job.name, job.trigger)
        return

    # SIGTERM (docker stop / `restart: unless-stopped`) doit arrêter proprement
    # le scheduler plutôt que de tuer un job d'ingestion en plein milieu d'écriture.
    def _handle_sigterm(signum, frame):
        log.info("Signal %s reçu, arrêt du scheduler...", signum)
        scheduler.shutdown(wait=False)

    signal.signal(signal.SIGTERM, _handle_sigterm)

    log.info("Scheduler démarré (timezone=%s). Ctrl+C pour arrêter.", scheduler.timezone)
    try:
        scheduler.start()
    except KeyboardInterrupt:
        log.info("Interruption clavier, arrêt du scheduler...")
        scheduler.shutdown(wait=False)


   if __name__ == "__main__":
       main()