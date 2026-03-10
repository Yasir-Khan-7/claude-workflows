#!/usr/bin/env python3
"""
Orchestrator for the ML Data Advisor pipeline.

Runs all three steps in sequence:
    1. Profile the dataset
    2. Recommend algorithms
    3. Generate training plan report

Usage:
    python tools/run_advisor.py --input data.csv --target label_column

    # Without a target column (defaults to unsupervised/clustering):
    python tools/run_advisor.py --input data.csv

    # Specify custom output directory:
    python tools/run_advisor.py --input data.csv --target label --output-dir .tmp/my_analysis

Outputs:
    .tmp/ml_advisor/profile.json           - Dataset profile
    .tmp/ml_advisor/recommendations.json   - Algorithm recommendations
    .tmp/ml_advisor/training_plan.md       - Full training plan report
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from profile_dataset import profile_dataset
from recommend_algorithms import recommend_algorithms
from generate_training_plan import generate_report


def run_pipeline(input_path: str, target_col: str | None = None, output_dir: str = ".tmp/ml_advisor") -> dict:
    """
    Run the full ML Data Advisor pipeline.

    Args:
        input_path: Path to dataset file.
        target_col: Optional target column name.
        output_dir: Directory for output files.

    Returns:
        Dict with paths to all generated files.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    results = {}
    total_start = time.time()

    print("=" * 60)
    print("  ML DATA ADVISOR — Full Pipeline")
    print("=" * 60)
    print(f"\n  Input:  {input_path}")
    print(f"  Target: {target_col or '(none — unsupervised mode)'}")
    print(f"  Output: {output_dir}/")
    print()

    print("─" * 60)
    print("  Step 1/3: Profiling Dataset...")
    print("─" * 60)
    step_start = time.time()

    profile = profile_dataset(input_path, target_col)
    profile_path = out / "profile.json"
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False, default=str)

    results["profile"] = str(profile_path)
    elapsed = time.time() - step_start
    print(f"  Done in {elapsed:.1f}s — {profile['shape']['rows']} rows, {profile['shape']['columns']} cols")
    print(f"  Quality Score: {profile['quality_score']['overall']}/100")
    print()

    print("─" * 60)
    print("  Step 2/3: Generating Algorithm Recommendations...")
    print("─" * 60)
    step_start = time.time()

    recommendations = recommend_algorithms(profile)
    rec_path = out / "recommendations.json"
    with open(rec_path, "w", encoding="utf-8") as f:
        json.dump(recommendations, f, indent=2, ensure_ascii=False)

    results["recommendations"] = str(rec_path)
    elapsed = time.time() - step_start
    approach = recommendations["recommended_approach"]["approach"]
    top_algo = recommendations["recommendations"][0]["name"] if recommendations["recommendations"] else "None"
    print(f"  Done in {elapsed:.1f}s")
    print(f"  Problem Type: {recommendations['problem_type']['problem_type']}")
    print(f"  Approach: {approach.upper()}")
    print(f"  Top Algorithm: {top_algo}")
    print(f"  Total Recommendations: {len(recommendations['recommendations'])}")
    print()

    print("─" * 60)
    print("  Step 3/3: Generating Training Plan Report...")
    print("─" * 60)
    step_start = time.time()

    report = generate_report(profile, recommendations)
    report_path = out / "training_plan.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    results["training_plan"] = str(report_path)
    elapsed = time.time() - step_start
    print(f"  Done in {elapsed:.1f}s")
    print()

    total_elapsed = time.time() - total_start
    print("=" * 60)
    print("  PIPELINE COMPLETE")
    print("=" * 60)
    print(f"\n  Total time: {total_elapsed:.1f}s")
    print(f"\n  Generated files:")
    for name, path in results.items():
        print(f"    {name}: {path}")
    print(f"\n  Open {results['training_plan']} for the full report.")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="ML Data Advisor — Analyze data and recommend the best ML/DL approach",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/run_advisor.py --input data.csv --target price
  python tools/run_advisor.py --input customers.parquet --target churn
  python tools/run_advisor.py --input reviews.json --target sentiment
  python tools/run_advisor.py --input data.csv  # unsupervised mode
        """,
    )
    parser.add_argument("--input", required=True, help="Path to dataset file (CSV, JSON, Parquet, Excel)")
    parser.add_argument("--target", default=None, help="Name of the target/label column (omit for unsupervised)")
    parser.add_argument("--output-dir", default=".tmp/ml_advisor", help="Output directory (default: .tmp/ml_advisor)")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    run_pipeline(args.input, args.target, args.output_dir)


if __name__ == "__main__":
    main()
