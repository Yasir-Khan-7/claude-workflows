#!/usr/bin/env python3
"""
End-to-end tests for the ML Data Advisor pipeline.

Tests all three tools (profile, recommend, report) against synthetic
datasets covering different problem types: binary classification,
multiclass, regression, text/NLP, and unsupervised clustering.

Usage:
    python tests/test_pipeline.py

    # Run from project root:
    cd ml-data-advisor && python tests/test_pipeline.py
"""

import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from profile_dataset import profile_dataset
from recommend_algorithms import recommend_algorithms
from generate_training_plan import generate_report


PASS = 0
FAIL = 0


def check(condition: bool, label: str) -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {label}")
    else:
        FAIL += 1
        print(f"  FAIL  {label}")


def _make_binary_classification_csv(path: str, n_rows: int = 1000) -> str:
    """Generate a synthetic binary classification dataset."""
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "age": rng.integers(18, 80, n_rows),
        "income": rng.normal(50000, 15000, n_rows).round(2),
        "credit_score": rng.integers(300, 850, n_rows),
        "loan_amount": rng.normal(20000, 8000, n_rows).round(2),
        "employment_years": rng.integers(0, 40, n_rows),
        "has_mortgage": rng.choice([0, 1], n_rows),
        "region": rng.choice(["North", "South", "East", "West"], n_rows),
        "default": rng.choice([0, 1], n_rows, p=[0.7, 0.3]),
    })
    df.loc[rng.choice(n_rows, 50, replace=False), "income"] = np.nan
    df.to_csv(path, index=False)
    return path


def _make_regression_csv(path: str, n_rows: int = 2000) -> str:
    """Generate a synthetic regression dataset."""
    rng = np.random.default_rng(42)
    sqft = rng.integers(500, 5000, n_rows)
    bedrooms = rng.integers(1, 6, n_rows)
    age = rng.integers(0, 100, n_rows)
    price = 50000 + 150 * sqft + 10000 * bedrooms - 500 * age + rng.normal(0, 20000, n_rows)

    df = pd.DataFrame({
        "sqft": sqft,
        "bedrooms": bedrooms,
        "bathrooms": rng.integers(1, 4, n_rows),
        "age_years": age,
        "garage": rng.choice(["yes", "no"], n_rows),
        "neighborhood": rng.choice(["A", "B", "C", "D", "E"], n_rows),
        "price": price.round(2),
    })
    df.to_csv(path, index=False)
    return path


def _make_multiclass_csv(path: str, n_rows: int = 800) -> str:
    """Generate a synthetic multiclass classification dataset."""
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "feature_1": rng.normal(0, 1, n_rows),
        "feature_2": rng.normal(0, 1, n_rows),
        "feature_3": rng.normal(0, 1, n_rows),
        "feature_4": rng.normal(0, 1, n_rows),
        "species": rng.choice(["setosa", "versicolor", "virginica"], n_rows),
    })
    df.to_csv(path, index=False)
    return path


def _make_text_csv(path: str, n_rows: int = 500) -> str:
    """Generate a synthetic text classification dataset."""
    rng = np.random.default_rng(42)
    positive_phrases = [
        "This product is amazing and I love it",
        "Great quality and fast shipping",
        "Exceeded my expectations, highly recommend",
        "Best purchase I have made this year",
        "Fantastic product, will buy again",
    ]
    negative_phrases = [
        "Terrible quality, broke after one day",
        "Worst product I have ever bought",
        "Complete waste of money, do not buy",
        "Very disappointed with this purchase",
        "Poor quality and slow delivery",
    ]

    reviews = []
    sentiments = []
    for _ in range(n_rows):
        if rng.random() > 0.4:
            reviews.append(rng.choice(positive_phrases) + " " + " ".join(rng.choice(["really", "very", "so", "quite"], 3)))
            sentiments.append("positive")
        else:
            reviews.append(rng.choice(negative_phrases) + " " + " ".join(rng.choice(["extremely", "absolutely", "truly"], 2)))
            sentiments.append("negative")

    df = pd.DataFrame({"review_text": reviews, "sentiment": sentiments})
    df.to_csv(path, index=False)
    return path


def _make_clustering_csv(path: str, n_rows: int = 600) -> str:
    """Generate a synthetic clustering dataset (no target)."""
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "annual_spend": rng.normal(5000, 2000, n_rows).round(2),
        "visit_frequency": rng.integers(1, 50, n_rows),
        "avg_basket_size": rng.normal(50, 20, n_rows).round(2),
        "days_since_last_visit": rng.integers(0, 365, n_rows),
        "loyalty_points": rng.integers(0, 10000, n_rows),
    })
    df.to_csv(path, index=False)
    return path


def test_binary_classification():
    print("\n--- Test: Binary Classification ---")
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        csv_path = _make_binary_classification_csv(f.name)

    profile = profile_dataset(csv_path, target_col="default")
    check(profile["shape"]["rows"] == 1000, "Row count is 1000")
    check(profile["shape"]["columns"] == 8, "Column count is 8")
    check("numeric" in profile["type_summary"], "Numeric columns detected")
    check("categorical" in profile["type_summary"], "Categorical columns detected")
    check(profile["quality_score"]["overall"] > 0, "Quality score computed")
    check(profile["target_analysis"]["problem_type"] == "binary_classification", "Problem type is binary classification")

    recs = recommend_algorithms(profile)
    check(recs["problem_type"]["problem_type"] == "binary_classification", "Recommender detects binary classification")
    check(len(recs["recommendations"]) >= 3, "At least 3 algorithms recommended")
    check(recs["recommended_approach"]["approach"] in ("ml", "ml_first"), "Recommends ML for 1000-row tabular data")

    algo_names = [r["algorithm_id"] for r in recs["recommendations"]]
    check("xgboost" in algo_names or "lightgbm" in algo_names or "random_forest" in algo_names,
          "At least one tree-based method recommended")

    check(len(recs["preprocessing_steps"]) >= 1, "At least 1 preprocessing step suggested")

    eval_strategy = recs["evaluation_strategy"]
    check("AUC-ROC" in eval_strategy["primary_metric"], "AUC-ROC is primary metric for binary classification")

    report = generate_report(profile, recs)
    check("# ML/DL Data Advisor Report" in report, "Report has title")
    check("Algorithm Recommendations" in report, "Report has algorithm section")
    check("Preprocessing Pipeline" in report, "Report has preprocessing section")
    check("```python" in report, "Report has code snippet")

    Path(csv_path).unlink(missing_ok=True)


def test_regression():
    print("\n--- Test: Regression ---")
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        csv_path = _make_regression_csv(f.name)

    profile = profile_dataset(csv_path, target_col="price")
    check(profile["shape"]["rows"] == 2000, "Row count is 2000")
    check(profile["target_analysis"]["problem_type"] == "regression", "Problem type is regression")

    recs = recommend_algorithms(profile)
    check(recs["problem_type"]["problem_type"] == "regression", "Recommender detects regression")
    check(recs["recommended_approach"]["approach"] in ("ml", "ml_first"), "Recommends ML for 2000-row tabular regression")

    eval_strategy = recs["evaluation_strategy"]
    check("RMSE" in eval_strategy["primary_metric"], "RMSE is primary metric for regression")

    report = generate_report(profile, recs)
    check("Regression" in report, "Report mentions regression")

    Path(csv_path).unlink(missing_ok=True)


def test_multiclass():
    print("\n--- Test: Multiclass Classification ---")
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        csv_path = _make_multiclass_csv(f.name)

    profile = profile_dataset(csv_path, target_col="species")
    check(profile["target_analysis"]["problem_type"] == "multiclass_classification",
          "Problem type is multiclass classification")
    check(profile["target_analysis"]["unique_values"] == 3, "3 unique classes detected")

    recs = recommend_algorithms(profile)
    check(recs["problem_type"]["problem_type"] == "multiclass_classification",
          "Recommender detects multiclass")

    eval_strategy = recs["evaluation_strategy"]
    check("F1" in eval_strategy["primary_metric"], "F1 is primary metric for multiclass")

    Path(csv_path).unlink(missing_ok=True)


def test_text_nlp():
    print("\n--- Test: Text/NLP Classification ---")
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        csv_path = _make_text_csv(f.name)

    profile = profile_dataset(csv_path, target_col="sentiment")
    check("text" in profile["type_summary"], "Text columns detected")
    check(profile["target_analysis"]["problem_type"] == "binary_classification",
          "Sentiment target is binary classification")

    recs = recommend_algorithms(profile)
    check(len(recs["recommendations"]) >= 2, "Multiple algorithms recommended")

    has_text_preprocessing = any("Text" in s["step"] for s in recs["preprocessing_steps"])
    check(has_text_preprocessing, "Text preprocessing step included")

    report = generate_report(profile, recs)
    check("Tool Ecosystem" in report, "Report has tool ecosystem section")

    Path(csv_path).unlink(missing_ok=True)


def test_unsupervised():
    print("\n--- Test: Unsupervised / Clustering ---")
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        csv_path = _make_clustering_csv(f.name)

    profile = profile_dataset(csv_path, target_col=None)
    check("target_analysis" not in profile, "No target analysis when target not specified")

    recs = recommend_algorithms(profile)
    check(recs["problem_type"]["problem_type"] == "clustering", "Defaults to clustering without target")

    algo_names = [r["algorithm_id"] for r in recs["recommendations"]]
    check("kmeans" in algo_names or "dbscan" in algo_names, "Clustering algorithm recommended")

    eval_strategy = recs["evaluation_strategy"]
    check("Silhouette" in eval_strategy["primary_metric"], "Silhouette score for clustering evaluation")

    Path(csv_path).unlink(missing_ok=True)


def test_quality_score():
    print("\n--- Test: Data Quality Score ---")
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        csv_path = f.name

    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "a": rng.normal(0, 1, 500),
        "b": rng.normal(0, 1, 500),
        "c": rng.choice(["x", "y", "z"], 500),
    })
    df.to_csv(csv_path, index=False)

    profile = profile_dataset(csv_path)
    quality = profile["quality_score"]
    check(0 <= quality["overall"] <= 100, "Quality score is in [0, 100]")
    check(quality["completeness"] > 90, "Completeness > 90% for clean data")
    check(quality["uniqueness"] > 50, "Uniqueness is reasonable")

    Path(csv_path).unlink(missing_ok=True)


def test_correlation_detection():
    print("\n--- Test: Correlation Detection ---")
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        csv_path = f.name

    rng = np.random.default_rng(42)
    x = rng.normal(0, 1, 500)
    df = pd.DataFrame({
        "x": x,
        "y": x * 0.99 + rng.normal(0, 0.01, 500),
        "z": rng.normal(0, 1, 500),
    })
    df.to_csv(csv_path, index=False)

    profile = profile_dataset(csv_path)
    check(len(profile["high_correlations"]) >= 1, "High correlation detected between x and y")
    if profile["high_correlations"]:
        check(profile["high_correlations"][0]["correlation"] > 0.9,
              "Correlation > 0.9 for near-duplicate features")

    Path(csv_path).unlink(missing_ok=True)


def test_full_orchestrator():
    print("\n--- Test: Full Pipeline Orchestration ---")
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        csv_path = _make_binary_classification_csv(f.name)

    with tempfile.TemporaryDirectory() as tmpdir:
        profile = profile_dataset(csv_path, target_col="default")
        profile_path = Path(tmpdir) / "profile.json"
        with open(profile_path, "w") as fp:
            json.dump(profile, fp, indent=2, default=str)

        recs = recommend_algorithms(profile)
        recs_path = Path(tmpdir) / "recommendations.json"
        with open(recs_path, "w") as fp:
            json.dump(recs, fp, indent=2)

        report = generate_report(profile, recs)
        report_path = Path(tmpdir) / "training_plan.md"
        with open(report_path, "w") as fp:
            fp.write(report)

        check(profile_path.exists(), "Profile JSON written")
        check(recs_path.exists(), "Recommendations JSON written")
        check(report_path.exists(), "Training plan MD written")
        check(len(report) > 1000, "Report is substantial (>1000 chars)")

    Path(csv_path).unlink(missing_ok=True)


def main():
    global PASS, FAIL

    print("=" * 60)
    print("  ML DATA ADVISOR — Test Suite")
    print("=" * 60)

    test_binary_classification()
    test_regression()
    test_multiclass()
    test_text_nlp()
    test_unsupervised()
    test_quality_score()
    test_correlation_detection()
    test_full_orchestrator()

    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"  Results: {PASS}/{total} passed, {FAIL} failed")
    print("=" * 60)

    if FAIL > 0:
        sys.exit(1)
    else:
        print("\n  All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
