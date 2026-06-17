"""
MediRAG FastAPI application.
Exposes:
  POST /oracle        - start an oracle analysis (returns session_id)
  WS   /ws/{session} - WebSocket stream of oracle events
  GET  /report/{sid} - download PDF report
  GET  /health        - health check
  /mcp               - MCP server (SSE transport)
"""
import json
import os
import tempfile
import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from backend.config import CORS_ORIGINS
from backend.graph_rag.neo4j_client import init_schema
from backend.services.file_parser import parse_file
from backend.services.oracle_engine import run_oracle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory session store (use Redis in production)
sessions: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        init_schema()
        logger.info("Neo4j schema initialized.")
    except Exception as e:
        logger.warning(f"Neo4j not available (will degrade gracefully): {e}")
    yield
    # Shutdown
    try:
        from backend.graph_rag.neo4j_client import close_driver
        close_driver()
    except Exception:
        pass


app = FastAPI(
    title="MediRAG Clinical Intelligence Oracle",
    description="Graph RAG + MCP medical diagnostic system. Not a chatbot.",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount MCP server
try:
    from backend.mcp_server.server import mcp
    app.mount("/mcp", mcp.streamable_http_app())
    logger.info("MCP server mounted at /mcp")
except Exception as e:
    logger.warning(f"MCP server mount failed: {e}")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "MediRAG Oracle v3.0"}


@app.post("/oracle/start")
async def start_oracle(
    patient_data: str = Form(...),
    file: UploadFile = File(None),
):
    """Create an oracle session and return session_id for WebSocket connection."""
    session_id = str(uuid.uuid4())
    patient = json.loads(patient_data)
    uploaded_text = ""

    if file and file.filename:
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        uploaded_text = parse_file(tmp_path, file.content_type or "")
        os.unlink(tmp_path)

    from backend.services.security import deidentify_text
    if patient.get("chief_complaint"):
        patient["chief_complaint"] = deidentify_text(patient["chief_complaint"])
    if patient.get("extra_context"):
        patient["extra_context"] = deidentify_text(patient["extra_context"])
    if patient.get("lab_notes"):
        patient["lab_notes"] = deidentify_text(patient["lab_notes"])
    if patient.get("family_history"):
        patient["family_history"] = deidentify_text(patient["family_history"])
    uploaded_text = deidentify_text(uploaded_text)

    sessions[session_id] = {
        "patient": patient,
        "uploaded_text": uploaded_text,
        "status": "ready",
        "result": None,
    }
    return {"session_id": session_id}


@app.websocket("/ws/{session_id}")
async def oracle_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint — streams all oracle events to frontend."""
    await websocket.accept()

    if session_id not in sessions:
        await websocket.send_json({"type": "error", "text": "Invalid session ID"})
        await websocket.close()
        return

    session = sessions[session_id]
    patient = session["patient"]
    uploaded_text = session["uploaded_text"]

    try:
        async for event in run_oracle(patient, uploaded_text):
            await websocket.send_json(event)
            # Cache the final answer
            if event.get("type") == "final_answer":
                session["result"] = event.get("data")
                session["status"] = "complete"
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"Oracle error: {e}")
        await websocket.send_json({"type": "error", "text": str(e)})
    finally:
        await websocket.close()


@app.get("/report/{session_id}")
async def download_report(session_id: str):
    """Generate and download PDF report for a completed session."""
    session = sessions.get(session_id)
    if not session or not session.get("result"):
        return JSONResponse(status_code=404, content={"error": "No result available for this session"})

    from backend.services.report_builder import generate_pdf_report
    output_path = f"./reports/{session_id}.pdf"
    os.makedirs("./reports", exist_ok=True)
    generate_pdf_report(session["patient"], session["result"], output_path)
    return FileResponse(output_path, media_type="application/pdf",
                        filename="MediRAG_Report.pdf")
