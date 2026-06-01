"""
FRIS — Pipeline orchestrator.

Runs ETL → EDA → Segmentation → Model as an async generator that yields
Server-Sent Events. Each heavy step runs in a ThreadPoolExecutor so the
asyncio event loop stays responsive during CPU-bound ML training.
"""

import asyncio
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Make root-level modules importable when backend/ is the working package
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fris_etl import run_etl
from fris_eda import run_eda
from fris_segmentation import run_segmentation
from fris_model import run_model


def _sse(event: str, data: dict) -> dict:
    return {"event": event, "data": json.dumps(data, default=str)}


async def run_pipeline(session_dir: Path, input_path: Path, sis_profile: str = "banner"):
    """
    Async generator that yields SSE-compatible dicts.

    Each dict has keys ``event`` and ``data`` (JSON string).
    Yields progress events as steps complete, then a final ``complete``
    event. Yields an ``error`` event if any step raises.

    Results are persisted to ``session_dir/results.json`` on completion
    so /api/results can serve them after a server restart.
    """
    loop = asyncio.get_event_loop()
    # max_workers=1: only one pipeline at a time per process.
    # sklearn CV is not thread-safe if multiple pipelines share resources;
    # each upload gets its own session dir, so state is fully isolated.
    executor = ThreadPoolExecutor(max_workers=1)
    combined: dict = {}

    # -- ETL ------------------------------------------------------------------
    yield _sse("progress", {
        "step": "etl", "status": "running", "pct": 5,
        "message": "Loading and cleaning borrower data…",
    })
    try:
        etl_result = await loop.run_in_executor(
            executor, run_etl, input_path, session_dir, sis_profile
        )
    except Exception as exc:
        yield _sse("error", {"step": "etl", "message": str(exc)})
        return
    combined["etl"] = etl_result
    yield _sse("progress", {
        "step": "etl", "status": "done", "pct": 25,
        "message": (
            f"ETL complete: {etl_result['valid_population']:,} students, "
            f"{etl_result['default_rate']:.1%} default rate"
        ),
        "summary": {
            "total_raw": etl_result["total_raw"],
            "defaults": etl_result["defaults"],
            "default_rate": etl_result["default_rate"],
        },
    })

    data_path = session_dir / "dataset_fris.csv"

    # -- EDA ------------------------------------------------------------------
    yield _sse("progress", {
        "step": "eda", "status": "running", "pct": 30,
        "message": "Computing distributions and correlations…",
    })
    try:
        eda_result = await loop.run_in_executor(executor, run_eda, data_path)
    except Exception as exc:
        yield _sse("error", {"step": "eda", "message": str(exc)})
        return
    combined["eda"] = eda_result
    yield _sse("progress", {
        "step": "eda", "status": "done", "pct": 50,
        "message": f"EDA complete — {eda_result['n_rows']:,} rows analysed",
    })

    # -- SEGMENTATION ---------------------------------------------------------
    yield _sse("progress", {
        "step": "segmentation", "status": "running", "pct": 55,
        "message": "Segmenting by level, GPA, campus, program…",
    })
    try:
        seg_result = await loop.run_in_executor(
            executor, run_segmentation, data_path, session_dir
        )
    except Exception as exc:
        yield _sse("error", {"step": "segmentation", "message": str(exc)})
        return
    combined["segmentation"] = seg_result
    yield _sse("progress", {
        "step": "segmentation", "status": "done", "pct": 75,
        "message": "Segmentation complete: 8 segment groups analysed",
    })

    # -- MODEL ----------------------------------------------------------------
    yield _sse("progress", {
        "step": "model", "status": "running", "pct": 80,
        "message": "Training 3 models with 5-fold CV (this takes ~30s)…",
    })
    try:
        model_result = await loop.run_in_executor(
            executor, run_model, data_path, session_dir
        )
    except Exception as exc:
        yield _sse("error", {"step": "model", "message": str(exc)})
        return
    combined["model"] = model_result
    yield _sse("progress", {
        "step": "model", "status": "done", "pct": 100,
        "message": (
            f"Best model: {model_result['best_model']} "
            f"(AUC = {model_result['best_auc']:.3f})"
        ),
        "summary": {
            "best_model": model_result["best_model"],
            "best_auc": model_result["best_auc"],
        },
    })

    # -- PERSIST RESULTS ------------------------------------------------------
    results_path = session_dir / "results.json"
    results_path.write_text(json.dumps(combined, default=str))

    yield _sse("complete", {
        "session_id": session_dir.name,
        "message": "Pipeline complete. Dashboard ready.",
    })
