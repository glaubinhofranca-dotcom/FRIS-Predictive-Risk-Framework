"""
FRIS — FastAPI application.

Endpoints
─────────
POST /api/upload           Accept .xlsx / .csv file, create session, return session_id
GET  /api/run              SSE stream — run pipeline, emit progress events
GET  /api/results          Return full results JSON for a completed session
GET  /api/static/{id}/{f}  Serve session chart PNGs (allowlisted filenames only)
GET  /                     Serve frontend SPA
"""

import json
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from backend.pipeline import run_pipeline

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
DATA_DIR = ROOT_DIR / "data" / "sessions"
DATA_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_CHART_FILENAMES = {"fris_model_results.png", "fris_segmentation.png"}
ALLOWED_EXTENSIONS = {".xlsx", ".xlsm", ".xls", ".csv"}

# ---------------------------------------------------------------------------
# In-memory session registry
# The results.json written to disk is the durable source; this dict only
# tracks live pipeline state so /api/run can avoid re-running a pipeline
# that is already in progress.
# ---------------------------------------------------------------------------
sessions: dict[str, dict] = {}

app = FastAPI(title="FRIS — Financial Risk Intelligence System", version="3.0")

# Serve frontend static assets (CSS, JS)
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    session_id = str(uuid.uuid4())
    session_dir = DATA_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    input_path = session_dir / f"input{suffix}"
    contents = await file.read()
    input_path.write_bytes(contents)

    sessions[session_id] = {
        "status": "uploaded",
        "input_path": input_path,
        "session_dir": session_dir,
    }

    return JSONResponse({
        "session_id": session_id,
        "filename": file.filename,
        "size_bytes": len(contents),
    })


@app.get("/api/run")
async def run(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found. Upload a file first.")

    sess = sessions[session_id]
    if sess["status"] == "running":
        raise HTTPException(status_code=409, detail="Pipeline already running for this session.")

    sess["status"] = "running"

    async def event_generator():
        try:
            async for event in run_pipeline(
                session_dir=sess["session_dir"],
                input_path=sess["input_path"],
            ):
                yield event
            sess["status"] = "complete"
        except Exception as exc:
            sess["status"] = "error"
            yield {"event": "error", "data": json.dumps({"message": str(exc)})}

    return EventSourceResponse(event_generator())


@app.get("/api/results")
async def results(session_id: str):
    if session_id not in sessions and not (DATA_DIR / session_id).exists():
        raise HTTPException(status_code=404, detail="Session not found.")

    session_dir = DATA_DIR / session_id
    results_path = session_dir / "results.json"

    if not results_path.exists():
        status = sessions.get(session_id, {}).get("status", "unknown")
        if status == "running":
            raise HTTPException(status_code=202, detail="Pipeline still running.")
        raise HTTPException(status_code=404, detail="Results not ready yet.")

    data = json.loads(results_path.read_text(encoding="utf-8"))
    data["session_id"] = session_id
    data["status"] = "complete"
    return JSONResponse(data)


@app.get("/api/static/{session_id}/{filename}")
async def serve_chart(session_id: str, filename: str):
    # Allowlist prevents directory traversal and exposure of sensitive data
    if filename not in ALLOWED_CHART_FILENAMES:
        raise HTTPException(status_code=403, detail="File not allowed.")

    file_path = DATA_DIR / session_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Chart not found.")

    return FileResponse(str(file_path), media_type="image/png")
