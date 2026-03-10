#!/usr/bin/env python3
"""
FastAPI backend for the ML Data Advisor.

Wraps the existing pipeline tools (profile, recommend, report) and adds
an optional Groq LLM deep-analysis layer for richer insights.

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
import requests
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from profile_dataset import profile_dataset
from recommend_algorithms import recommend_algorithms
from generate_training_plan import generate_report

app = FastAPI(title="ML Data Advisor", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


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
    """Run the full ML Data Advisor pipeline on an uploaded dataset."""
    start = time.time()

    suffix = Path(file.filename).suffix
    if suffix.lower() not in (".csv", ".json", ".parquet", ".xls", ".xlsx"):
        return {"error": f"Unsupported file format: {suffix}. Use CSV, JSON, Parquet, or Excel."}

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        target_col = target.strip() if target.strip() else None
        profile = profile_dataset(tmp_path, target_col)
        recommendations = recommend_algorithms(profile)
        report_md = generate_report(profile, recommendations)

        groq_insights = None
        if groq_key.strip():
            groq_insights = _call_groq_analysis(groq_key.strip(), profile, recommendations)

        elapsed = round(time.time() - start, 2)

        return JSONResponse(content=_sanitize({
            "success": True,
            "elapsed_seconds": elapsed,
            "profile": profile,
            "recommendations": recommendations,
            "report_markdown": report_md,
            "groq_insights": groq_insights,
        }))

    except Exception as e:
        return {"error": str(e)}
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _call_groq_analysis(api_key: str, profile: dict, recommendations: dict) -> dict | None:
    """Call Groq LLM for deeper, conversational analysis."""
    problem = recommendations["problem_type"]
    approach = recommendations["recommended_approach"]
    top_algos = recommendations["recommendations"][:3]
    target = profile.get("target_analysis", {})
    quality = profile.get("quality_score", {})

    algo_summary = "\n".join(
        f"  {i+1}. {a['name']} (score: {a['suitability_score']}/100) — {', '.join(a['reasons'][:2])}"
        for i, a in enumerate(top_algos)
    )

    prompt = f"""You are a senior ML engineer reviewing a dataset analysis. Give practical, actionable advice.

DATASET SUMMARY:
- File: {profile.get('file', 'unknown')}
- Shape: {profile['shape']['rows']} rows x {profile['shape']['columns']} columns
- Types: {json.dumps(profile.get('type_summary', {}))}
- Quality Score: {quality.get('overall', 'N/A')}/100
- Completeness: {quality.get('completeness', 'N/A')}%
- Problem Type: {problem.get('problem_type', 'unknown')}
- Target Column: {target.get('column', 'None')}
- Imbalanced: {target.get('is_imbalanced', 'N/A')} (ratio: {target.get('imbalance_ratio', 'N/A')})

RECOMMENDED APPROACH: {approach.get('approach', 'unknown').upper()}
Reason: {approach.get('reason', '')}

TOP ALGORITHMS:
{algo_summary}

PREPROCESSING STEPS: {len(recommendations.get('preprocessing_steps', []))} steps identified

Please provide:
1. **Quick Assessment** (2-3 sentences) — Is this data ready for ML? Any red flags?
2. **Strategy Recommendation** (3-4 sentences) — What approach would you take as a senior ML engineer? Why?
3. **Common Pitfalls** (3 bullet points) — What mistakes should the engineer avoid with this specific data?
4. **Quick Win** (1-2 sentences) — What's the fastest path to a working baseline model?
5. **Advanced Tip** (1-2 sentences) — One advanced technique that could give a performance edge.

Keep it concise, practical, and specific to THIS dataset. No generic advice."""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are a senior machine learning engineer giving practical advice. Be concise and specific."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 1500,
    }

    try:
        resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"analysis": text, "model": GROQ_MODEL, "status": "success"}
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else "unknown"
        if status == 401:
            return {"analysis": "", "status": "error", "message": "Invalid Groq API key. Please check and try again."}
        return {"analysis": "", "status": "error", "message": f"Groq API error (HTTP {status}): {str(e)}"}
    except Exception as e:
        return {"analysis": "", "status": "error", "message": f"Groq request failed: {str(e)}"}
