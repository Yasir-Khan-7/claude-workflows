#!/usr/bin/env python3
"""
FastAPI backend for the ML Data Advisor.

Architecture (WAT Framework):
    - Tool Layer:  profile_dataset.py (deterministic data profiling)
    - Agent Layer: llm_advisor.py (LLM reasons about algorithms, preprocessing, strategy)
    - Tool Layer:  generate_training_plan.py (deterministic report generation)

The LLM agent is REQUIRED for analysis. No API key = no analysis.
This follows the WAT principle: AI handles reasoning, tools handle execution.

Usage:
    cd ml-data-advisor
    uvicorn web.app:app --reload --port 8000
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from profile_dataset import profile_dataset
from generate_training_plan import generate_report
from llm_advisor import get_llm_recommendations

app = FastAPI(title="ML Data Advisor", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")


def _sanitize(obj):
    """Recursively convert numpy types to native Python for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


@app.get("/", response_class=HTMLResponse)
async def root():
    return (WEB_DIR / "static" / "index.html").read_text()


@app.post("/api/analyze")
async def analyze_dataset(
    file: UploadFile = File(...),
    target: str = Form(""),
    groq_key: str = Form(""),
):
    """
    Run the ML Data Advisor pipeline.

    REQUIRES a Groq API key. The LLM Agent handles all reasoning:
    problem type, algorithm selection, preprocessing, and evaluation.
    """
    start = time.time()

    if not groq_key.strip():
        return {"error": "Groq API key is required. The AI agent needs an LLM to reason about your data. Get a free key at https://console.groq.com/keys"}

    suffix = Path(file.filename).suffix
    if suffix.lower() not in (".csv", ".json", ".parquet", ".xls", ".xlsx"):
        return {"error": f"Unsupported file format: {suffix}. Use CSV, JSON, Parquet, or Excel."}

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        target_col = target.strip() if target.strip() else None

        # TOOL: Deterministic data profiling
        profile = profile_dataset(tmp_path, target_col)

        # AGENT: LLM reasons about the profile dynamically
        llm_result = get_llm_recommendations(profile, groq_key.strip())

        if "error" in llm_result:
            return {"error": f"AI Agent error: {llm_result['error']}"}

        recommendations = llm_result
        deep_analysis = llm_result.get("deep_analysis")

        # TOOL: Deterministic report generation
        report_md = generate_report(profile, recommendations)

        elapsed = round(time.time() - start, 2)

        return JSONResponse(content=_sanitize({
            "success": True,
            "elapsed_seconds": elapsed,
            "analysis_mode": "agent",
            "profile": profile,
            "recommendations": recommendations,
            "report_markdown": report_md,
            "deep_analysis": deep_analysis,
            "model": llm_result.get("_meta", {}).get("model"),
        }))

    except Exception as e:
        return {"error": str(e)}
    finally:
        Path(tmp_path).unlink(missing_ok=True)
