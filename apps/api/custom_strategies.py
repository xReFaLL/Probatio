"""
Sprint 7 — Endpoints des stratégies custom utilisateur.

Relie l'éditeur Monaco (apps/web/components/CustomStrategyEditor.tsx) au
sandbox d'exécution (packages/backtest-engine/sandbox/) et aux moteurs de
backtest existants (engine_vectorized/engine_event_driven, inchangés depuis
les Sprints 4/6). Suit le même pattern que apps/api/backtests.py : toute la
logique métier vit ici, main.py ne fait qu'inclure le router.

Trois familles d'opérations :
  - CRUD sur les stratégies custom (créer, lister, versionner le code)
  - test rapide (échantillon réduit, retour détaillé pour l'édition)
  - backtest complet (réutilise ENGINE_REGISTRY de backtests.py -- la
    stratégie custom, une fois convertie en Series de positions par le
    sandbox, est indiscernable d'une stratégie interne pour le moteur)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "packages" / "data-pipeline"))
sys.path.insert(0, str(ROOT / "packages" / "backtest-engine"))

from fastapi import APIRouter, HTTPException  # noqa: E402

from custom_strategy import CustomStrategyError, generate_signals_sandboxed, quick_test_sandboxed  # noqa: E402
from metrics import compute_metrics  # noqa: E402
from warehouse_reader import load_ohlcv  # noqa: E402

from .backtests import ENGINE_REGISTRY, _sanitize_metrics  # noqa: E402
from .db import (  # noqa: E402
    create_backtest_run,
    create_custom_strategy,
    get_connection,
    get_custom_strategy,
    get_or_create_instrument,
    get_strategy_code_version,
    insert_backtest_result,
    insert_equity_curve,
    insert_trades,
    list_custom_strategies,
    list_strategy_execution_logs,
    log_strategy_execution,
    save_strategy_code,
)
from .schemas import (  # noqa: E402
    BacktestResultOut,
    CustomStrategyBacktestRequest,
    CustomStrategyCreateRequest,
    CustomStrategyOut,
    CustomStrategySummaryOut,
    CustomStrategyTestRequest,
    CustomStrategyTestResultOut,
    CustomStrategyUpdateCodeRequest,
    ExecutionLogOut,
)

router = APIRouter()


def _to_out(strategy: dict, versions: list) -> CustomStrategyOut:
    return CustomStrategyOut(
        strategy_id=strategy["id"],
        name=strategy["name"],
        description=strategy["description"],
        created_at=strategy["created_at"],
        updated_at=strategy["updated_at"],
        versions=[
            {"id": v["id"], "mode": v["mode"], "version": v["version"], "created_at": v["created_at"]}
            for v in versions
        ],
    )


@router.post("/custom-strategies", response_model=CustomStrategyOut)
def create_custom_strategy_endpoint(req: CustomStrategyCreateRequest):
    con = get_connection()
    try:
        strategy_id = create_custom_strategy(con, name=req.name, description=req.description)
        save_strategy_code(con, strategy_id, code=req.code, mode=req.mode)
        con.commit()
        strategy, versions = get_custom_strategy(con, strategy_id)
    finally:
        con.close()
    return _to_out(strategy, versions)


@router.get("/custom-strategies", response_model=list[CustomStrategySummaryOut])
def list_custom_strategies_endpoint(limit: int = 50):
    con = get_connection()
    try:
        rows = list_custom_strategies(con, limit=limit)
    finally:
        con.close()
    return [
        CustomStrategySummaryOut(
            strategy_id=r["strategy_id"], name=r["name"], description=r["description"],
            created_at=r["created_at"], updated_at=r["updated_at"],
            latest_version=r["latest_version"], latest_mode=r["latest_mode"],
        )
        for r in rows
    ]


@router.get("/custom-strategies/{strategy_id}", response_model=CustomStrategyOut)
def get_custom_strategy_endpoint(strategy_id: int):
    con = get_connection()
    try:
        strategy, versions = get_custom_strategy(con, strategy_id)
    finally:
        con.close()
    if strategy is None:
        raise HTTPException(status_code=404, detail=f"Stratégie custom {strategy_id} introuvable")
    return _to_out(strategy, versions)


@router.post("/custom-strategies/{strategy_id}/versions", response_model=CustomStrategyOut)
def add_code_version_endpoint(strategy_id: int, req: CustomStrategyUpdateCodeRequest):
    con = get_connection()
    try:
        strategy, _ = get_custom_strategy(con, strategy_id)
        if strategy is None:
            raise HTTPException(status_code=404, detail=f"Stratégie custom {strategy_id} introuvable")
        save_strategy_code(con, strategy_id, code=req.code, mode=req.mode)
        con.commit()
        strategy, versions = get_custom_strategy(con, strategy_id)
    finally:
        con.close()
    return _to_out(strategy, versions)


@router.get("/custom-strategies/{strategy_id}/logs", response_model=list[ExecutionLogOut])
def list_execution_logs_endpoint(strategy_id: int, limit: int = 20):
    con = get_connection()
    try:
        strategy, _ = get_custom_strategy(con, strategy_id)
        if strategy is None:
            raise HTTPException(status_code=404, detail=f"Stratégie custom {strategy_id} introuvable")
        rows = list_strategy_execution_logs(con, strategy_id, limit=limit)
    finally:
        con.close()
    return [
        ExecutionLogOut(
            id=r["id"], run_id=r["run_id"], version=r["version"], kind=r["kind"], status=r["status"],
            stdout=r["stdout"], stderr=r["stderr"], execution_time_ms=r["execution_time_ms"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.post("/custom-strategies/test", response_model=CustomStrategyTestResultOut)
def test_custom_strategy_endpoint(req: CustomStrategyTestRequest):
    """
    Test rapide sur échantillon réduit, code fourni directement (pas besoin
    d'avoir sauvegardé la stratégie) -- pensé pour un retour immédiat pendant
    l'édition dans Monaco, avant de sauvegarder quoi que ce soit. Aucune
    persistance (pas de strategy_execution_logs -- il n'y a pas de
    strategy_code_id tant que le code n'est pas sauvegardé).
    """
    try:
        df = load_ohlcv(req.symbol, req.asset_class)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    result = quick_test_sandboxed(df, req.params, req.code, req.mode)
    return CustomStrategyTestResultOut(
        status=result.status, positions=result.positions, timestamps=result.timestamps,
        errors=result.errors, error=result.error, traceback=result.traceback,
        stdout=result.stdout, stderr=result.stderr, execution_time_ms=result.execution_time_ms,
    )


@router.post("/custom-strategies/{strategy_id}/backtest", response_model=BacktestResultOut)
def backtest_custom_strategy_endpoint(strategy_id: int, req: CustomStrategyBacktestRequest):
    """
    Backtest complet à partir d'une stratégie custom sauvegardée. Réutilise
    exactement ENGINE_REGISTRY de backtests.py -- une fois le sandbox
    exécuté et converti en Series de positions (custom_strategy.py), le
    moteur ne fait plus de différence avec une stratégie interne.
    """
    con = get_connection()
    try:
        strategy, versions = get_custom_strategy(con, strategy_id)
        if strategy is None:
            raise HTTPException(status_code=404, detail=f"Stratégie custom {strategy_id} introuvable")

        version = req.version or versions[0]["version"]  # versions triées version DESC
        code_row = get_strategy_code_version(con, strategy_id, version)
        if code_row is None:
            raise HTTPException(status_code=404, detail=f"Version {version} introuvable pour cette stratégie")

        try:
            df = load_ohlcv(req.symbol, req.asset_class, start=req.start_date, end=req.end_date)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

        try:
            positions = generate_signals_sandboxed(df, req.params, code_row["code"], code_row["mode"])
            exec_status, exec_error = "ok", None
        except CustomStrategyError as e:
            exec_status = e.sandbox_result.status
            exec_error = str(e)

        # On journalise l'exécution (succès ou échec) avant de décider si on
        # continue -- même un run échoué est une info utile pour l'utilisateur
        # (voir GET /custom-strategies/{id}/logs).
        log_strategy_execution(
            con, strategy_code_id=code_row["id"], kind="full_run", status=exec_status,
            stdout="", stderr=exec_error or "", execution_time_ms=0,
        )
        con.commit()

        if exec_status != "ok":
            raise HTTPException(status_code=422, detail=exec_error)

        run_engine = ENGINE_REGISTRY[req.engine]
        engine_kwargs = {"commission": req.commission, "slippage": req.slippage}
        if req.engine == "event_driven":
            engine_kwargs["position_size"] = req.position_size

        result = run_engine(df, positions, initial_capital=req.initial_capital, **engine_kwargs)
        metrics = _sanitize_metrics(
            compute_metrics(result["equity_curve"], result["trades"], req.initial_capital)
        )

        actual_start = str(df["timestamp"].min())
        actual_end = str(df["timestamp"].max())

        instrument_id = get_or_create_instrument(con, req.symbol, req.asset_class)
        run_id = create_backtest_run(
            con, strategy_id, instrument_id, timeframe="1d",
            start_date=actual_start, end_date=actual_end,
            initial_capital=req.initial_capital, commission=req.commission,
            slippage=req.slippage,
            params_json=__import__("json").dumps(
                {"strategy": strategy["name"], "custom": True, "version": version,
                 "params": req.params, "engine": req.engine}
            ),
            engine=req.engine,
        )
        insert_backtest_result(con, run_id, metrics)
        insert_trades(con, run_id, instrument_id, result["trades"])
        insert_equity_curve(con, run_id, result["equity_curve"])
        con.commit()
    finally:
        con.close()

    return BacktestResultOut(
        run_id=run_id,
        symbol=req.symbol,
        asset_class=req.asset_class,
        strategy=strategy["name"],
        engine=req.engine,
        params=req.params,
        start_date=actual_start,
        end_date=actual_end,
        initial_capital=req.initial_capital,
        metrics=metrics,
        equity_curve=[
            {"timestamp": str(ts), "equity": float(eq)}
            for ts, eq in zip(result["equity_curve"]["timestamp"], result["equity_curve"]["equity"])
        ],
        trades=[
            {**t, "entry_time": str(t["entry_time"]), "exit_time": str(t["exit_time"])}
            for t in result["trades"]
        ],
    )