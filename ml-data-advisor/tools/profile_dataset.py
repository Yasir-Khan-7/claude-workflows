#!/usr/bin/env python3
"""
Profile a dataset to extract structural and statistical metadata.

This is the first step in the ML Data Advisor pipeline. It inspects
the dataset (CSV, JSON, Parquet) and produces a structured profile
that downstream tools use to make algorithm recommendations.

Usage:
    python tools/profile_dataset.py --input data.csv --output .tmp/profile.json

Outputs:
    Structured JSON profile with:
    - Shape (rows, columns)
    - Column types (numeric, categorical, text, datetime, binary)
    - Missing value stats
    - Cardinality per column
    - Statistical summaries (mean, std, skew for numerics)
    - Target variable analysis (if --target is specified)
    - Data quality score
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


def _detect_column_type(series: pd.Series) -> str:
    """Classify a pandas Series into a semantic type."""
    if series.dtype in ("datetime64[ns]", "datetime64[ns, UTC]"):
        return "datetime"

    if pd.api.types.is_bool_dtype(series):
        return "binary"

    if pd.api.types.is_numeric_dtype(series):
        unique_vals = series.dropna().unique()
        if len(unique_vals) <= 2 and set(unique_vals).issubset({0, 1, 0.0, 1.0, True, False}):
            return "binary"
        if pd.api.types.is_integer_dtype(series) and len(unique_vals) < 20:
            return "categorical_numeric"
        return "numeric"

    if pd.api.types.is_string_dtype(series) or series.dtype == object:
        non_null = series.dropna()
        if len(non_null) == 0:
            return "unknown"

        avg_len = non_null.astype(str).str.len().mean()
        nunique = non_null.nunique()

        if avg_len > 100:
            return "text"

        try:
            pd.to_datetime(non_null.head(20), infer_datetime_format=True)
            return "datetime"
        except (ValueError, TypeError):
            pass

        if nunique <= 50 or (nunique / len(non_null)) < 0.05:
            return "categorical"
        if avg_len > 50:
            return "text"
        return "categorical"

    return "unknown"


def _numeric_stats(series: pd.Series) -> dict:
    """Compute statistical summary for a numeric column."""
    clean = series.dropna()
    if len(clean) == 0:
        return {}

    stats = {
        "mean": round(float(clean.mean()), 4),
        "std": round(float(clean.std()), 4),
        "min": round(float(clean.min()), 4),
        "max": round(float(clean.max()), 4),
        "median": round(float(clean.median()), 4),
        "q25": round(float(clean.quantile(0.25)), 4),
        "q75": round(float(clean.quantile(0.75)), 4),
    }

    try:
        stats["skewness"] = round(float(clean.skew()), 4)
        stats["kurtosis"] = round(float(clean.kurtosis()), 4)
    except (ValueError, TypeError):
        pass

    iqr = stats["q75"] - stats["q25"]
    if iqr > 0:
        lower = stats["q25"] - 1.5 * iqr
        upper = stats["q75"] + 1.5 * iqr
        outlier_count = int(((clean < lower) | (clean > upper)).sum())
        stats["outlier_count"] = outlier_count
        stats["outlier_pct"] = round(outlier_count / len(clean) * 100, 2)

    return stats


def _categorical_stats(series: pd.Series) -> dict:
    """Compute summary for a categorical column."""
    clean = series.dropna()
    if len(clean) == 0:
        return {}

    value_counts = clean.value_counts()
    top_values = value_counts.head(10).to_dict()

    return {
        "unique_count": int(clean.nunique()),
        "top_values": {str(k): int(v) for k, v in top_values.items()},
        "mode": str(value_counts.index[0]) if len(value_counts) > 0 else None,
        "entropy": round(float(-sum(
            (c / len(clean)) * np.log2(c / len(clean))
            for c in value_counts.values if c > 0
        )), 4),
    }


def _analyze_target(df: pd.DataFrame, target_col: str) -> dict:
    """Analyze the target variable to determine the problem type."""
    if target_col not in df.columns:
        return {"error": f"Target column '{target_col}' not found in dataset"}

    series = df[target_col]
    col_type = _detect_column_type(series)
    nunique = series.nunique()
    n_rows = len(series)

    target_info = {
        "column": target_col,
        "dtype": str(series.dtype),
        "semantic_type": col_type,
        "unique_values": int(nunique),
        "missing_count": int(series.isna().sum()),
        "missing_pct": round(float(series.isna().mean() * 100), 2),
    }

    if col_type in ("binary",):
        target_info["problem_type"] = "binary_classification"
        vc = series.value_counts()
        target_info["class_distribution"] = {str(k): int(v) for k, v in vc.items()}
        if len(vc) == 2:
            minority = vc.min()
            majority = vc.max()
            target_info["imbalance_ratio"] = round(float(majority / minority), 2)
            target_info["is_imbalanced"] = (majority / minority) > 3.0

    elif col_type in ("categorical", "categorical_numeric"):
        if nunique == 2:
            target_info["problem_type"] = "binary_classification"
            vc = series.value_counts()
            target_info["class_distribution"] = {str(k): int(v) for k, v in vc.items()}
            minority = vc.min()
            majority = vc.max()
            target_info["imbalance_ratio"] = round(float(majority / minority), 2)
            target_info["is_imbalanced"] = (majority / minority) > 3.0
        elif nunique <= 20:
            target_info["problem_type"] = "multiclass_classification"
            vc = series.value_counts()
            target_info["class_distribution"] = {str(k): int(v) for k, v in vc.head(20).items()}
            if len(vc) >= 2:
                target_info["imbalance_ratio"] = round(float(vc.max() / vc.min()), 2)
                target_info["is_imbalanced"] = (vc.max() / vc.min()) > 3.0
        else:
            target_info["problem_type"] = "regression"
            target_info["note"] = "High cardinality categorical treated as regression"

    elif col_type == "numeric":
        if nunique <= 2:
            target_info["problem_type"] = "binary_classification"
        elif nunique <= 20 and (nunique / n_rows) < 0.01:
            target_info["problem_type"] = "multiclass_classification"
            vc = series.value_counts()
            target_info["class_distribution"] = {str(k): int(v) for k, v in vc.items()}
        else:
            target_info["problem_type"] = "regression"
            target_info["stats"] = _numeric_stats(series)

    elif col_type == "text":
        target_info["problem_type"] = "nlp_generation"
        target_info["avg_length"] = round(float(series.dropna().astype(str).str.len().mean()), 1)

    else:
        target_info["problem_type"] = "unknown"

    return target_info


def _compute_quality_score(df: pd.DataFrame, column_profiles: list) -> dict:
    """Compute an overall data quality score (0-100)."""
    scores = {}

    total_cells = df.shape[0] * df.shape[1]
    missing_cells = df.isna().sum().sum()
    scores["completeness"] = round((1 - missing_cells / total_cells) * 100, 1) if total_cells > 0 else 0

    duplicate_rows = df.duplicated().sum()
    scores["uniqueness"] = round((1 - duplicate_rows / len(df)) * 100, 1) if len(df) > 0 else 0

    constant_cols = sum(1 for cp in column_profiles if cp.get("unique_count", cp.get("stats", {}).get("std", 1)) in (0, 1))
    scores["variability"] = round((1 - constant_cols / len(column_profiles)) * 100, 1) if column_profiles else 0

    scores["size_adequacy"] = min(100.0, round(len(df) / 100 * 10, 1))

    weights = {"completeness": 0.35, "uniqueness": 0.2, "variability": 0.2, "size_adequacy": 0.25}
    scores["overall"] = round(sum(scores[k] * weights[k] for k in weights), 1)

    return scores


def _detect_correlations(df: pd.DataFrame) -> list:
    """Find highly correlated numeric feature pairs."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if len(numeric_cols) < 2:
        return []

    corr_matrix = df[numeric_cols].corr()
    high_corr = []
    seen = set()

    for i, col1 in enumerate(numeric_cols):
        for j, col2 in enumerate(numeric_cols):
            if i >= j:
                continue
            val = corr_matrix.iloc[i, j]
            if abs(val) > 0.8 and (col1, col2) not in seen:
                high_corr.append({
                    "feature_1": col1,
                    "feature_2": col2,
                    "correlation": round(float(val), 4),
                    "strength": "very_high" if abs(val) > 0.95 else "high",
                })
                seen.add((col1, col2))

    return sorted(high_corr, key=lambda x: abs(x["correlation"]), reverse=True)[:20]


def profile_dataset(filepath: str, target_col: str | None = None) -> dict:
    """
    Profile a dataset and return structured metadata.

    Args:
        filepath: Path to CSV, JSON, or Parquet file.
        target_col: Optional name of the target/label column.

    Returns:
        Dict with dataset profile including shape, types, stats, quality score.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {filepath}")

    ext = path.suffix.lower()
    if ext == ".csv":
        df = pd.read_csv(filepath, low_memory=False)
    elif ext == ".json":
        df = pd.read_json(filepath)
    elif ext == ".parquet":
        df = pd.read_parquet(filepath)
    elif ext in (".xls", ".xlsx"):
        df = pd.read_excel(filepath)
    else:
        raise ValueError(f"Unsupported file format: {ext}. Use CSV, JSON, Parquet, or Excel.")

    n_rows, n_cols = df.shape
    column_profiles = []

    for col in df.columns:
        series = df[col]
        sem_type = _detect_column_type(series)

        col_profile = {
            "name": col,
            "dtype": str(series.dtype),
            "semantic_type": sem_type,
            "missing_count": int(series.isna().sum()),
            "missing_pct": round(float(series.isna().mean() * 100), 2),
            "unique_count": int(series.nunique()),
        }

        if sem_type in ("numeric", "categorical_numeric"):
            col_profile["stats"] = _numeric_stats(series)
        elif sem_type in ("categorical", "binary"):
            col_profile.update(_categorical_stats(series))
        elif sem_type == "text":
            non_null = series.dropna().astype(str)
            col_profile["avg_length"] = round(float(non_null.str.len().mean()), 1) if len(non_null) > 0 else 0
            col_profile["max_length"] = int(non_null.str.len().max()) if len(non_null) > 0 else 0
            col_profile["avg_word_count"] = round(float(non_null.str.split().str.len().mean()), 1) if len(non_null) > 0 else 0

        column_profiles.append(col_profile)

    type_summary = {}
    for cp in column_profiles:
        t = cp["semantic_type"]
        type_summary[t] = type_summary.get(t, 0) + 1

    quality = _compute_quality_score(df, column_profiles)
    correlations = _detect_correlations(df)

    profile = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "file": str(path.name),
        "file_size_mb": round(path.stat().st_size / (1024 * 1024), 2),
        "shape": {"rows": n_rows, "columns": n_cols},
        "type_summary": type_summary,
        "columns": column_profiles,
        "duplicate_rows": int(df.duplicated().sum()),
        "quality_score": quality,
        "high_correlations": correlations,
    }

    if target_col:
        profile["target_analysis"] = _analyze_target(df, target_col)

    return profile


def main():
    parser = argparse.ArgumentParser(description="Profile a dataset for ML/DL analysis")
    parser.add_argument("--input", required=True, help="Path to dataset file (CSV, JSON, Parquet, Excel)")
    parser.add_argument("--target", default=None, help="Name of the target/label column")
    parser.add_argument("--output", required=True, help="Path to write profile JSON")
    args = parser.parse_args()

    print(f"Profiling dataset: {args.input}")
    profile = profile_dataset(args.input, args.target)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nDataset Profile:")
    print(f"  Shape: {profile['shape']['rows']} rows x {profile['shape']['columns']} columns")
    print(f"  Types: {profile['type_summary']}")
    print(f"  Quality Score: {profile['quality_score']['overall']}/100")
    if profile.get("target_analysis"):
        ta = profile["target_analysis"]
        print(f"  Target: {ta['column']} -> {ta.get('problem_type', 'unknown')}")
    print(f"\nProfile saved to {args.output}")


if __name__ == "__main__":
    main()
