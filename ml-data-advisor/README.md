# ML Data Advisor

An AI-powered workflow that analyzes any dataset and tells you **whether to use Machine Learning or Deep Learning**, which specific algorithms are the best fit, how to preprocess your data, and what tools to use — all generated automatically from your data's characteristics.

Built on the **WAT framework** (Workflows, Agents, Tools).

## What It Does

Drop in a dataset, and the ML Data Advisor will:

1. **Profile your data** — detect column types, compute statistics, assess data quality, find correlations
2. **Recommend algorithms** — score 15+ algorithms against your data profile, rank by suitability
3. **Generate a training plan** — produce a full Markdown report with code snippets, preprocessing pipeline, evaluation strategy, and tool recommendations

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   PROFILER   │────▶│  RECOMMENDER │────▶│   REPORTER   │
│              │     │              │     │              │
│ Detect types │     │ Score algos  │     │ Generate     │
│ Compute stats│     │ ML vs DL     │     │ training     │
│ Quality score│     │ Preprocessing│     │ plan report  │
└─────────────┘     └──────────────┘     └──────────────┘
     ▼                    ▼                    ▼
 profile.json    recommendations.json    training_plan.md
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the full pipeline on your dataset
python tools/run_advisor.py --input your_data.csv --target label_column

# Without a target (unsupervised/clustering mode)
python tools/run_advisor.py --input your_data.csv

# Output appears in .tmp/ml_advisor/
```

## Example Output

For a 1,500-row credit default dataset:

- **Problem Type:** Binary Classification
- **Recommended Approach:** Classical ML
- **Top Algorithm:** XGBoost (score: 75/100)
- **Preprocessing:** Encode categoricals, scale features
- **Evaluation:** AUC-ROC with Stratified 5-Fold CV
- **Full report with starter code** in `training_plan.md`

## Supported Problem Types

| Problem Type | How Detected |
|-------------|--------------|
| Binary Classification | Target has 2 unique values |
| Multiclass Classification | Target has 3-20 unique values |
| Regression | Target is continuous numeric |
| NLP / Text Classification | Text columns present with categorical target |
| Clustering | No target column specified |
| Anomaly Detection | Very imbalanced or no target |

## Algorithm Catalog (15+ algorithms scored)

| Family | Algorithms |
|--------|-----------|
| Linear | Logistic Regression, Linear Regression, Ridge, Lasso |
| Ensemble | Random Forest |
| Boosting | XGBoost, LightGBM |
| Kernel | SVM |
| Instance | KNN |
| Deep Learning (Tabular) | Neural Networks, TabNet |
| Deep Learning (NLP) | LSTM/RNN, Transformers (BERT) |
| Deep Learning (Vision) | CNN (ResNet, EfficientNet) |
| Clustering | K-Means, DBSCAN |
| Anomaly Detection | Isolation Forest, Autoencoder |

## Tools

| Tool | Purpose |
|------|---------|
| `tools/profile_dataset.py` | Profile dataset: types, stats, quality, correlations |
| `tools/recommend_algorithms.py` | Score and rank algorithms, generate preprocessing advice |
| `tools/generate_training_plan.py` | Compile Markdown report with code snippets |
| `tools/run_advisor.py` | Orchestrator — runs all steps in sequence |

## Running Individual Steps

```bash
# Step 1: Profile
python tools/profile_dataset.py --input data.csv --target label --output .tmp/profile.json

# Step 2: Recommend
python tools/recommend_algorithms.py --profile .tmp/profile.json --output .tmp/recommendations.json

# Step 3: Report
python tools/generate_training_plan.py --profile .tmp/profile.json --recommendations .tmp/recommendations.json --output .tmp/training_plan.md
```

## Testing

```bash
# Run the full test suite (44 tests across 8 scenarios)
python tests/test_pipeline.py
```

Tests cover: binary classification, regression, multiclass, text/NLP, unsupervised clustering, data quality scoring, correlation detection, and full pipeline orchestration.

## Supported File Formats

CSV, JSON, Parquet, Excel (.xls, .xlsx)

## Dependencies

- pandas, numpy, scikit-learn (core)
- No API keys required — runs entirely offline

## For AI Agents (Claude Code / Cursor)

Read `workflows/analyze_data.md` for the full SOP. The workflow follows the WAT pattern:

1. Agent reads the workflow
2. Runs tools in sequence
3. Handles errors gracefully
4. Delivers the training plan report

Multi-agent orchestration is supported — see the workflow for the architecture diagram.
