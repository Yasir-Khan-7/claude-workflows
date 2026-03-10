#!/usr/bin/env python3
"""
LLM-powered ML/DL Advisor Agent.

This is the Agent layer of the WAT framework. Instead of hardcoded rules,
it sends the dataset profile to an LLM and lets the model reason about
which algorithms, preprocessing steps, and evaluation strategies are best.

The deterministic profiling (profile_dataset.py) feeds structured data
into this agent, which then applies expert-level ML reasoning.

Usage:
    from llm_advisor import get_llm_recommendations
    result = get_llm_recommendations(profile, api_key)
"""

import json
import requests
from datetime import datetime, timezone

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """You are a world-class ML/AI engineer with 15+ years of experience.
You analyze dataset profiles and provide expert recommendations.

You MUST respond with valid JSON only — no markdown, no backticks, no explanation outside the JSON.

Your response must follow this exact schema:
{
  "problem_type": {
    "problem_type": "<binary_classification|multiclass_classification|regression|clustering|nlp_classification|anomaly_detection>",
    "confidence": "<high|medium|low>",
    "reasoning": "<1-2 sentence explanation>"
  },
  "recommended_approach": {
    "approach": "<ml|dl|ml_first>",
    "reason": "<1-2 sentence explanation>",
    "explanation": "<detailed 2-3 sentence explanation of what this approach means>"
  },
  "recommendations": [
    {
      "name": "<Algorithm Name>",
      "algorithm_id": "<snake_case_id>",
      "family": "<ml_linear|ml_ensemble|ml_boosting|ml_kernel|ml_instance|ml_clustering|ml_anomaly|dl_feedforward|dl_transformer|dl_recurrent|dl_convolutional|dl_generative>",
      "suitability_score": <0-100>,
      "reasons": ["<reason 1>", "<reason 2>", "<reason 3>"],
      "strengths": ["<strength 1>", "<strength 2>"],
      "weaknesses": ["<weakness 1>", "<weakness 2>"],
      "libraries": {"<lib_name>": "<import path>"},
      "hyperparameters": {"<param>": "<suggested value and range>"},
      "needs_scaling": <true|false>,
      "interpretable": <true|false>,
      "starter_code": "<2-5 line Python code snippet to get started>"
    }
  ],
  "preprocessing_steps": [
    {
      "step": "<Step Name>",
      "reason": "<Why this step is needed for THIS dataset>",
      "approaches": ["<approach 1>", "<approach 2>"],
      "tools": ["<sklearn.module.Class>"],
      "priority": "<critical|recommended|optional>"
    }
  ],
  "evaluation_strategy": {
    "primary_metric": "<metric name>",
    "metrics": ["<metric 1>", "<metric 2>"],
    "validation_strategy": "<description>",
    "tools": ["<sklearn.module>"]
  },
  "deep_analysis": {
    "quick_assessment": "<2-3 sentences: Is this data ready? Red flags?>",
    "strategy": "<3-4 sentences: What approach would a senior ML engineer take?>",
    "pitfalls": ["<pitfall 1>", "<pitfall 2>", "<pitfall 3>"],
    "quick_win": "<1-2 sentences: Fastest path to a baseline>",
    "advanced_tip": "<1-2 sentences: One technique for a performance edge>"
  }
}

IMPORTANT RULES:
1. Recommend 3-8 algorithms, ranked by suitability score (highest first)
2. Suitability scores must reflect THIS specific dataset, not generic rankings
3. Consider dataset size, types, quality, and problem type in your scoring
4. Preprocessing steps must be ordered by execution priority
5. Be specific to THIS dataset — no generic advice
6. For small datasets (<100 rows), prefer simple models and warn about overfitting
7. For imbalanced data, boost scores for algorithms with built-in imbalance handling
8. Include starter_code for each algorithm — real, runnable Python
9. If no target column, it's clustering/unsupervised
10. Your JSON must be parseable — no trailing commas, no comments"""


def _build_profile_summary(profile: dict) -> str:
    """Convert a dataset profile into a concise text summary for the LLM."""
    shape = profile["shape"]
    quality = profile.get("quality_score", {})
    type_summary = profile.get("type_summary", {})
    target = profile.get("target_analysis", {})
    columns = profile.get("columns", [])
    high_corr = profile.get("high_correlations", [])

    lines = [
        "=== DATASET PROFILE ===",
        f"File: {profile.get('file', 'unknown')}",
        f"Size: {shape['rows']} rows x {shape['columns']} columns ({profile.get('file_size_mb', 0)} MB)",
        f"Duplicate Rows: {profile.get('duplicate_rows', 0)}",
        "",
        "--- Quality Scores ---",
        f"Overall: {quality.get('overall', 'N/A')}/100",
        f"Completeness: {quality.get('completeness', 'N/A')}%",
        f"Uniqueness: {quality.get('uniqueness', 'N/A')}%",
        f"Variability: {quality.get('variability', 'N/A')}%",
        f"Size Adequacy: {quality.get('size_adequacy', 'N/A')}%",
        "",
        "--- Column Type Distribution ---",
    ]
    for t, c in type_summary.items():
        lines.append(f"  {t}: {c}")

    lines.append("")
    lines.append("--- Column Details ---")
    for col in columns[:20]:
        line = f"  {col['name']} ({col['semantic_type']}, {col['dtype']}): {col.get('unique_count', '?')} unique, {col.get('missing_pct', 0)}% missing"
        if col.get("stats"):
            s = col["stats"]
            line += f" | mean={s.get('mean','?')}, std={s.get('std','?')}, skew={s.get('skewness','?')}, outliers={s.get('outlier_pct',0)}%"
        lines.append(line)

    if target:
        lines.append("")
        lines.append("--- Target Variable ---")
        lines.append(f"Column: {target.get('column', 'NONE')}")
        lines.append(f"Detected Type: {target.get('semantic_type', 'unknown')}")
        lines.append(f"Problem Type (from profiler): {target.get('problem_type', 'unknown')}")
        lines.append(f"Unique Values: {target.get('unique_values', 'N/A')}")
        lines.append(f"Missing: {target.get('missing_pct', 0)}%")
        if target.get("class_distribution"):
            lines.append(f"Class Distribution: {json.dumps(target['class_distribution'])}")
        if target.get("is_imbalanced"):
            lines.append(f"IMBALANCED: ratio={target.get('imbalance_ratio', '?')}:1")
        if target.get("stats"):
            s = target["stats"]
            lines.append(f"Stats: mean={s.get('mean')}, std={s.get('std')}, min={s.get('min')}, max={s.get('max')}")

    if high_corr:
        lines.append("")
        lines.append(f"--- High Correlations ({len(high_corr)} pairs) ---")
        for pair in high_corr[:10]:
            f1 = pair.get('feature_1') or pair.get('col_1', '?')
            f2 = pair.get('feature_2') or pair.get('col_2', '?')
            lines.append(f"  {f1} <-> {f2}: r={pair['correlation']}")

    return "\n".join(lines)


def get_llm_recommendations(profile: dict, api_key: str, model: str = None) -> dict:
    """
    Send the dataset profile to an LLM and get dynamic, reasoned recommendations.

    This is the Agent layer of the WAT framework — the LLM handles reasoning
    while the tool handles the API call and response parsing.

    Args:
        profile: Structured dataset profile from profile_dataset.py
        api_key: Groq API key
        model: Override the default model

    Returns:
        Dict with recommendations in the same schema the frontend expects,
        plus a 'deep_analysis' section with expert insights.
        On failure, returns a dict with 'error' key.
    """
    use_model = model or GROQ_MODEL
    profile_text = _build_profile_summary(profile)

    user_prompt = f"""Analyze this dataset profile and provide ML/DL recommendations.

{profile_text}

Respond with JSON following the schema from your instructions. Be specific to THIS dataset."""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": use_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 4000,
        "response_format": {"type": "json_object"},
    }

    try:
        resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=45)
        resp.raise_for_status()
        data = resp.json()
        raw_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        result = json.loads(raw_text)
        result["_meta"] = {
            "source": "llm_agent",
            "model": use_model,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tokens_used": data.get("usage", {}),
        }
        return _normalize_response(result)

    except json.JSONDecodeError as e:
        return {"error": f"LLM returned invalid JSON: {e}", "raw": raw_text[:500]}
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else "unknown"
        if status == 401:
            return {"error": "Invalid API key"}
        body = ""
        try:
            body = e.response.json().get("error", {}).get("message", "")
        except Exception:
            pass
        return {"error": f"Groq API error (HTTP {status}): {body or str(e)}"}
    except requests.exceptions.Timeout:
        return {"error": "LLM request timed out (45s). Try again or use a smaller dataset."}
    except Exception as e:
        return {"error": f"LLM advisor failed: {str(e)}"}


def _normalize_response(result: dict) -> dict:
    """Ensure the LLM response has all required fields with correct types."""
    if "problem_type" not in result:
        result["problem_type"] = {"problem_type": "unknown", "confidence": "low", "reasoning": ""}
    if "recommended_approach" not in result:
        result["recommended_approach"] = {"approach": "ml", "reason": "", "explanation": ""}
    if "recommendations" not in result:
        result["recommendations"] = []
    if "preprocessing_steps" not in result:
        result["preprocessing_steps"] = []
    if "evaluation_strategy" not in result:
        result["evaluation_strategy"] = {"primary_metric": "TBD", "metrics": [], "validation_strategy": "TBD", "tools": []}
    if "deep_analysis" not in result:
        result["deep_analysis"] = {}

    for algo in result["recommendations"]:
        algo.setdefault("suitability_score", 50)
        algo.setdefault("reasons", [])
        algo.setdefault("strengths", [])
        algo.setdefault("weaknesses", [])
        algo.setdefault("libraries", {})
        algo.setdefault("hyperparameters", {})
        algo.setdefault("needs_scaling", False)
        algo.setdefault("interpretable", False)
        algo.setdefault("starter_code", "")
        algo.setdefault("family", "unknown")
        algo.setdefault("name", algo.get("algorithm_id", "Unknown"))

    result["recommendations"].sort(key=lambda x: x.get("suitability_score", 0), reverse=True)

    return result
