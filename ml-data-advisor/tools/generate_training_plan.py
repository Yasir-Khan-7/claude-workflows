#!/usr/bin/env python3
"""
Generate a comprehensive training plan and final report.

This is the final step in the ML Data Advisor pipeline. It combines
the dataset profile and algorithm recommendations into an actionable
training plan with code snippets, tool suggestions, and a structured
Markdown report.

Usage:
    python tools/generate_training_plan.py \
        --profile .tmp/profile.json \
        --recommendations .tmp/recommendations.json \
        --output .tmp/training_plan.md

Outputs:
    Markdown report with:
    - Executive summary (ML vs DL decision, why)
    - Dataset overview
    - Algorithm recommendations with code snippets
    - Preprocessing pipeline
    - Evaluation strategy
    - Tool ecosystem map
    - Next steps checklist
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent


def _format_quality_bar(score: float) -> str:
    filled = int(score / 10)
    return f"{'█' * filled}{'░' * (10 - filled)} {score}/100"


def _code_snippet_for_algo(algo: dict, problem_type: str) -> str:
    """Generate a starter code snippet for the top algorithm."""
    algo_id = algo["algorithm_id"]
    name = algo["name"]

    snippets = {
        "xgboost": dedent("""\
            import xgboost as xgb
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import classification_report, roc_auc_score

            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

            model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                eval_metric='logloss',
                early_stopping_rounds=20,
                random_state=42,
            )
            model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

            y_pred = model.predict(X_test)
            y_prob = model.predict_proba(X_test)[:, 1]
            print(classification_report(y_test, y_pred))
            print(f"AUC-ROC: {roc_auc_score(y_test, y_prob):.4f}")"""),

        "lightgbm": dedent("""\
            import lightgbm as lgb
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import classification_report

            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

            model = lgb.LGBMClassifier(
                n_estimators=300,
                max_depth=-1,
                num_leaves=63,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
            )
            model.fit(
                X_train, y_train,
                eval_set=[(X_test, y_test)],
                callbacks=[lgb.early_stopping(20), lgb.log_evaluation(50)],
            )
            print(classification_report(y_test, model.predict(X_test)))"""),

        "random_forest": dedent("""\
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import cross_val_score

            model = RandomForestClassifier(
                n_estimators=200,
                max_depth=None,
                min_samples_leaf=2,
                max_features='sqrt',
                random_state=42,
                n_jobs=-1,
            )
            scores = cross_val_score(model, X, y, cv=5, scoring='f1_macro')
            print(f"F1 (5-fold CV): {scores.mean():.4f} ± {scores.std():.4f}")

            model.fit(X_train, y_train)
            importances = model.feature_importances_"""),

        "logistic_regression": dedent("""\
            from sklearn.linear_model import LogisticRegression
            from sklearn.preprocessing import StandardScaler
            from sklearn.pipeline import Pipeline
            from sklearn.model_selection import cross_val_score

            pipe = Pipeline([
                ('scaler', StandardScaler()),
                ('clf', LogisticRegression(C=1.0, penalty='l2', max_iter=1000, random_state=42)),
            ])
            scores = cross_val_score(pipe, X, y, cv=5, scoring='roc_auc')
            print(f"AUC-ROC (5-fold CV): {scores.mean():.4f} ± {scores.std():.4f}")"""),

        "linear_regression": dedent("""\
            from sklearn.linear_model import Ridge
            from sklearn.preprocessing import StandardScaler
            from sklearn.pipeline import Pipeline
            from sklearn.model_selection import cross_val_score

            pipe = Pipeline([
                ('scaler', StandardScaler()),
                ('reg', Ridge(alpha=1.0)),
            ])
            scores = cross_val_score(pipe, X, y, cv=5, scoring='neg_root_mean_squared_error')
            print(f"RMSE (5-fold CV): {-scores.mean():.4f} ± {scores.std():.4f}")"""),

        "neural_network_tabular": dedent("""\
            import torch
            import torch.nn as nn
            from torch.utils.data import DataLoader, TensorDataset

            class TabularNet(nn.Module):
                def __init__(self, input_dim, output_dim):
                    super().__init__()
                    self.net = nn.Sequential(
                        nn.Linear(input_dim, 256),
                        nn.ReLU(),
                        nn.Dropout(0.3),
                        nn.Linear(256, 128),
                        nn.ReLU(),
                        nn.Dropout(0.2),
                        nn.Linear(128, output_dim),
                    )

                def forward(self, x):
                    return self.net(x)

            model = TabularNet(input_dim=X_train.shape[1], output_dim=num_classes)
            optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
            criterion = nn.CrossEntropyLoss()"""),

        "transformer": dedent("""\
            from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments

            model_name = "distilbert-base-uncased"
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=num_classes)

            training_args = TrainingArguments(
                output_dir="./results",
                num_train_epochs=3,
                per_device_train_batch_size=16,
                per_device_eval_batch_size=32,
                learning_rate=2e-5,
                weight_decay=0.01,
                evaluation_strategy="epoch",
                save_strategy="epoch",
                load_best_model_at_end=True,
            )
            trainer = Trainer(model=model, args=training_args, train_dataset=train_ds, eval_dataset=val_ds)
            trainer.train()"""),

        "kmeans": dedent("""\
            from sklearn.cluster import KMeans
            from sklearn.preprocessing import StandardScaler
            from sklearn.metrics import silhouette_score

            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            # Elbow method to find optimal K
            inertias = []
            K_range = range(2, 11)
            for k in K_range:
                km = KMeans(n_clusters=k, n_init=10, random_state=42)
                km.fit(X_scaled)
                inertias.append(km.inertia_)

            # Fit with best K
            best_k = 4  # Replace with elbow point
            model = KMeans(n_clusters=best_k, n_init=10, random_state=42)
            labels = model.fit_predict(X_scaled)
            print(f"Silhouette Score: {silhouette_score(X_scaled, labels):.4f}")"""),
    }

    default_snippet = dedent(f"""\
        # {name} — see library documentation for implementation
        # Recommended libraries: {', '.join(algo.get('libraries', {}).keys())}
        # Key hyperparameters to tune:
        #   {chr(10).join(f'  {k}: {v}' for k, v in algo.get('hyperparameters', {}).items())}""")

    snippet = snippets.get(algo_id, default_snippet)

    if "regression" in problem_type and algo_id == "xgboost":
        snippet = snippet.replace("XGBClassifier", "XGBRegressor")
        snippet = snippet.replace("classification_report", "mean_squared_error")
        snippet = snippet.replace("roc_auc_score", "r2_score")
        snippet = snippet.replace("stratify=y, ", "")
        snippet = snippet.replace("logloss", "rmse")

    if "regression" in problem_type and algo_id == "lightgbm":
        snippet = snippet.replace("LGBMClassifier", "LGBMRegressor")
        snippet = snippet.replace("classification_report", "mean_squared_error, r2_score")

    if "regression" in problem_type and algo_id == "random_forest":
        snippet = snippet.replace("RandomForestClassifier", "RandomForestRegressor")
        snippet = snippet.replace("f1_macro", "neg_root_mean_squared_error")

    return snippet


def _tool_ecosystem_section(recommendations: dict) -> str:
    """Build a tool ecosystem reference section."""
    tools = {
        "Data Loading & EDA": [
            ("pandas", "Data manipulation and analysis", "pip install pandas"),
            ("numpy", "Numerical computing", "pip install numpy"),
            ("matplotlib / seaborn", "Visualization", "pip install matplotlib seaborn"),
            ("ydata-profiling", "Automated EDA reports", "pip install ydata-profiling"),
        ],
        "Classical ML": [
            ("scikit-learn", "Core ML library (models, preprocessing, metrics)", "pip install scikit-learn"),
            ("xgboost", "Gradient boosting (tabular SOTA)", "pip install xgboost"),
            ("lightgbm", "Fast gradient boosting", "pip install lightgbm"),
            ("catboost", "Boosting with native categorical support", "pip install catboost"),
            ("imbalanced-learn", "Resampling for class imbalance", "pip install imbalanced-learn"),
        ],
        "Deep Learning": [
            ("pytorch", "Flexible deep learning framework", "pip install torch torchvision"),
            ("tensorflow / keras", "Production-grade deep learning", "pip install tensorflow"),
            ("huggingface transformers", "Pre-trained NLP models", "pip install transformers"),
            ("fastai", "High-level deep learning API", "pip install fastai"),
        ],
        "Experiment Tracking": [
            ("MLflow", "Experiment tracking and model registry", "pip install mlflow"),
            ("Weights & Biases", "Experiment dashboard", "pip install wandb"),
            ("Optuna", "Hyperparameter optimization", "pip install optuna"),
        ],
        "Deployment": [
            ("ONNX", "Model interchange format", "pip install onnx onnxruntime"),
            ("FastAPI", "API serving", "pip install fastapi uvicorn"),
            ("BentoML", "ML model serving platform", "pip install bentoml"),
        ],
    }

    lines = ["## Tool Ecosystem Reference\n"]
    for category, items in tools.items():
        lines.append(f"### {category}\n")
        lines.append("| Tool | Purpose | Install |")
        lines.append("|------|---------|---------|")
        for name, purpose, install in items:
            lines.append(f"| **{name}** | {purpose} | `{install}` |")
        lines.append("")

    return "\n".join(lines)


def generate_report(profile: dict, recommendations: dict) -> str:
    """Generate a comprehensive Markdown training plan report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    problem = recommendations["problem_type"]
    approach = recommendations["recommended_approach"]
    quality = profile.get("quality_score", {})
    target = profile.get("target_analysis", {})

    lines = []

    lines.append(f"# ML/DL Data Advisor Report")
    lines.append(f"\n**Generated:** {now}")
    lines.append(f"**Dataset:** {profile.get('file', 'unknown')}")
    lines.append(f"**Rows:** {profile['shape']['rows']:,} | **Columns:** {profile['shape']['columns']}")
    lines.append(f"**Problem Type:** {problem['problem_type'].replace('_', ' ').title()}")
    lines.append(f"**Recommended Approach:** {approach['approach'].upper()}")
    lines.append("")

    lines.append("---\n")
    lines.append("## Executive Summary\n")
    lines.append(f"Based on analysis of your dataset ({profile['shape']['rows']:,} rows, "
                 f"{profile['shape']['columns']} features), the recommended approach is "
                 f"**{approach['approach'].replace('_', ' ').upper()}**.\n")
    lines.append(f"> {approach['reason']}\n")
    lines.append(f"{approach['explanation']}\n")

    if target:
        if target.get("is_imbalanced"):
            lines.append(f"**Warning:** Class imbalance detected (ratio {target.get('imbalance_ratio', '?')}:1). "
                        f"The preprocessing pipeline includes resampling strategies.\n")

    lines.append("---\n")
    lines.append("## Dataset Overview\n")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| **Rows** | {profile['shape']['rows']:,} |")
    lines.append(f"| **Columns** | {profile['shape']['columns']} |")
    lines.append(f"| **File Size** | {profile.get('file_size_mb', '?')} MB |")
    lines.append(f"| **Duplicate Rows** | {profile.get('duplicate_rows', 0):,} |")
    lines.append(f"| **Quality Score** | {_format_quality_bar(quality.get('overall', 0))} |")
    lines.append("")

    lines.append("### Column Types\n")
    lines.append("| Type | Count |")
    lines.append("|------|-------|")
    for t, count in sorted(profile.get("type_summary", {}).items()):
        lines.append(f"| {t.replace('_', ' ').title()} | {count} |")
    lines.append("")

    lines.append("### Quality Breakdown\n")
    lines.append("| Dimension | Score |")
    lines.append("|-----------|-------|")
    for dim in ("completeness", "uniqueness", "variability", "size_adequacy"):
        val = quality.get(dim, 0)
        lines.append(f"| {dim.replace('_', ' ').title()} | {_format_quality_bar(val)} |")
    lines.append("")

    if target:
        lines.append("### Target Variable\n")
        lines.append(f"| Property | Value |")
        lines.append(f"|----------|-------|")
        lines.append(f"| **Column** | `{target.get('column', '?')}` |")
        lines.append(f"| **Problem Type** | {target.get('problem_type', '?').replace('_', ' ').title()} |")
        lines.append(f"| **Unique Values** | {target.get('unique_values', '?')} |")
        lines.append(f"| **Missing** | {target.get('missing_pct', 0)}% |")
        if target.get("is_imbalanced") is not None:
            lines.append(f"| **Imbalanced** | {'Yes' if target['is_imbalanced'] else 'No'} "
                        f"(ratio {target.get('imbalance_ratio', '?')}:1) |")
        lines.append("")

        if target.get("class_distribution"):
            lines.append("**Class Distribution:**\n")
            lines.append("| Class | Count |")
            lines.append("|-------|-------|")
            for cls, count in target["class_distribution"].items():
                lines.append(f"| {cls} | {count:,} |")
            lines.append("")

    lines.append("---\n")
    lines.append("## Algorithm Recommendations\n")
    lines.append(f"Ranked by suitability score (higher = better fit for your data):\n")

    for i, rec in enumerate(recommendations["recommendations"][:5], 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"#{i}")
        lines.append(f"### {medal} {rec['name']} — Score: {rec['suitability_score']}/100\n")

        lines.append(f"**Family:** {rec['family'].replace('_', ' ').title()}")
        lines.append(f"**Interpretable:** {'Yes' if rec['interpretable'] else 'No'}")
        lines.append(f"**Needs Scaling:** {'Yes' if rec['needs_scaling'] else 'No'}\n")

        lines.append("**Why this algorithm:**")
        for reason in rec["reasons"]:
            lines.append(f"- {reason}")
        lines.append("")

        lines.append("**Strengths:**")
        for s in rec["strengths"][:4]:
            lines.append(f"- {s}")
        lines.append("")

        lines.append("**Key Hyperparameters:**\n")
        lines.append("| Parameter | Guidance |")
        lines.append("|-----------|----------|")
        for param, guidance in rec["hyperparameters"].items():
            lines.append(f"| `{param}` | {guidance} |")
        lines.append("")

        lines.append("**Libraries:**\n")
        for lib, usage in rec["libraries"].items():
            lines.append(f"- `{lib}`: `{usage}`")
        lines.append("")

        if i == 1:
            snippet = _code_snippet_for_algo(rec, problem["problem_type"])
            lines.append("**Starter Code:**\n")
            lines.append("```python")
            lines.append(snippet)
            lines.append("```\n")

    lines.append("---\n")
    lines.append("## Preprocessing Pipeline\n")
    lines.append(f"Execute these steps before training (in order):\n")

    for i, step in enumerate(recommendations["preprocessing_steps"], 1):
        lines.append(f"### Step {i}: {step['step']}\n")
        lines.append(f"**Why:** {step['reason']}\n")
        lines.append("**Approaches:**")
        for a in step["approaches"]:
            lines.append(f"- {a}")
        lines.append("")
        lines.append("**Tools:**")
        for t in step["tools"]:
            lines.append(f"- `{t}`")
        lines.append("")

    lines.append("---\n")
    evaluation = recommendations.get("evaluation_strategy", {})
    lines.append("## Evaluation Strategy\n")
    lines.append(f"**Primary Metric:** {evaluation.get('primary_metric', 'TBD')}\n")
    lines.append(f"**Validation:** {evaluation.get('validation_strategy', 'TBD')}\n")
    lines.append("**All Metrics:**")
    for m in evaluation.get("metrics", []):
        lines.append(f"- {m}")
    lines.append("")

    lines.append(_tool_ecosystem_section(recommendations))

    lines.append("---\n")
    lines.append("## Next Steps Checklist\n")
    checklist = [
        "Load and inspect your data with pandas",
        "Run the preprocessing pipeline (handle missing values, encode, scale)",
        "Split data into train/validation/test sets",
        f"Train the top recommended model ({recommendations['recommendations'][0]['name'] if recommendations['recommendations'] else 'TBD'})",
        "Evaluate with the recommended metrics",
        "Tune hyperparameters (Optuna or GridSearchCV)",
        "Compare with 2-3 alternative algorithms",
        "If ML plateaus and data is large, try the deep learning alternative",
        "Set up experiment tracking (MLflow or W&B)",
        "Document results and prepare for deployment",
    ]
    for item in checklist:
        lines.append(f"- [ ] {item}")
    lines.append("")

    lines.append("---\n")
    lines.append(f"*Report generated by ML Data Advisor — WAT Framework*\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate ML/DL training plan report")
    parser.add_argument("--profile", required=True, help="Path to dataset profile JSON")
    parser.add_argument("--recommendations", required=True, help="Path to recommendations JSON")
    parser.add_argument("--output", required=True, help="Path to write Markdown report")
    args = parser.parse_args()

    with open(args.profile, encoding="utf-8") as f:
        profile = json.load(f)
    with open(args.recommendations, encoding="utf-8") as f:
        recommendations = json.load(f)

    print(f"Generating training plan report...")
    report = generate_report(profile, recommendations)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Report saved to {args.output}")
    print(f"  Sections: Executive Summary, Dataset Overview, Algorithm Recommendations,")
    print(f"            Preprocessing Pipeline, Evaluation Strategy, Tool Ecosystem, Next Steps")


if __name__ == "__main__":
    main()
