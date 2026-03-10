# Workflow: ML/DL Data Advisor

## Objective
Analyze a dataset provided by an AI/ML engineer, determine whether Machine Learning or Deep Learning is the best fit, recommend specific algorithms ranked by suitability, generate preprocessing guidance, and produce a comprehensive training plan — all without requiring the engineer to manually inspect the data first.

## When to Use
- When an AI engineer has a new dataset and needs to decide which approach (ML vs DL) to use
- When selecting the right algorithm for a specific problem type (classification, regression, NLP, clustering, anomaly detection)
- When you need a structured preprocessing and evaluation plan before training
- When onboarding to a new ML project and need a data-driven starting point
- As a pre-training checklist to avoid common mistakes (wrong metric, missing preprocessing, etc.)

## Required Inputs

| Input | Source | Example |
|-------|--------|---------|
| Dataset file | User provides | `data.csv`, `customers.parquet`, `reviews.json` |
| Target column (optional) | User provides | `price`, `churn`, `sentiment` |
| File format | Auto-detected | CSV, JSON, Parquet, Excel |

**No API keys required.** This workflow runs entirely offline using local Python tools.

## Tools Used

| Tool | Purpose |
|------|---------|
| `tools/profile_dataset.py` | Profile the dataset: detect types, compute stats, assess quality, analyze target |
| `tools/recommend_algorithms.py` | Score and rank 15+ algorithms against the profile; generate preprocessing advice |
| `tools/generate_training_plan.py` | Compile everything into a structured Markdown report with code snippets |
| `tools/run_advisor.py` | Orchestrator — runs all three steps in sequence |

## Procedure

### Step 1: Profile the Dataset

```bash
python tools/profile_dataset.py --input data.csv --target label_column --output .tmp/ml_advisor/profile.json
```

- Loads the dataset (CSV, JSON, Parquet, or Excel)
- Detects column types: numeric, categorical, text, datetime, binary
- Computes per-column statistics (mean, std, skew, outliers for numerics; cardinality, entropy for categoricals)
- Analyzes the target variable to determine problem type (binary classification, multiclass, regression, NLP, clustering)
- Detects class imbalance, missing values, highly correlated features
- Computes an overall data quality score (0-100) across completeness, uniqueness, variability, and size adequacy
- Outputs structured JSON to `.tmp/ml_advisor/profile.json`

**If this fails:**
- File not found: Check the path. The tool accepts relative and absolute paths.
- Unsupported format: Convert to CSV first (`pandas.to_csv()`)
- Memory error: For very large files (>1GB), sample first: `head -n 100000 data.csv > data_sample.csv`
- Encoding error: Try `--encoding utf-8` or `latin-1` (not yet implemented — save the file with UTF-8 encoding)

### Step 2: Generate Algorithm Recommendations

```bash
python tools/recommend_algorithms.py --profile .tmp/ml_advisor/profile.json --output .tmp/ml_advisor/recommendations.json
```

- Reads the dataset profile from Step 1
- Infers the problem type (from target analysis or heuristics)
- Scores 15+ algorithms from a built-in catalog against the profile
- Scoring considers: data size, feature types, missing values, imbalance, correlations, and problem type
- Makes the ML vs DL decision with reasoning
- Generates preprocessing steps (imputation, encoding, scaling, text preprocessing, imbalance handling)
- Suggests evaluation metrics and validation strategy
- Outputs ranked recommendations to `.tmp/ml_advisor/recommendations.json`

**Decision Logic (ML vs DL):**

| Condition | Recommendation |
|-----------|---------------|
| Text/NLP task | **Deep Learning** (Transformers) |
| Image task | **Deep Learning** (CNN) |
| Rows > 50K and features > 100 | **Deep Learning** |
| Rows < 5K | **Classical ML** (more data-efficient) |
| Everything else | **Start with ML**, try DL if plateaus |

**If this fails:** Check that the profile JSON exists and is valid. Re-run Step 1 if needed.

### Step 3: Generate Training Plan Report

```bash
python tools/generate_training_plan.py --profile .tmp/ml_advisor/profile.json --recommendations .tmp/ml_advisor/recommendations.json --output .tmp/ml_advisor/training_plan.md
```

- Reads both the profile and recommendations
- Generates a comprehensive Markdown report with:
  - Executive summary (ML vs DL decision with reasoning)
  - Dataset overview (shape, types, quality scores)
  - Top 5 algorithm recommendations with scores, reasoning, hyperparameters, and libraries
  - Starter code snippet for the #1 algorithm
  - Preprocessing pipeline (ordered steps)
  - Evaluation strategy (metrics, validation approach)
  - Tool ecosystem reference (libraries for every phase)
  - Next steps checklist
- Outputs `.tmp/ml_advisor/training_plan.md`

**If this fails:** Check that both input JSON files exist.

### One-Shot: Run Full Pipeline

```bash
python tools/run_advisor.py --input data.csv --target label_column
```

This runs all three steps in sequence and produces all output files.

## Expected Outputs

| Output | Location |
|--------|----------|
| Dataset profile | `.tmp/ml_advisor/profile.json` |
| Algorithm recommendations | `.tmp/ml_advisor/recommendations.json` |
| **Training plan report** | `.tmp/ml_advisor/training_plan.md` |

## Report Format

The Markdown report includes:

- **Executive Summary**: ML vs DL decision, key reasoning, warnings
- **Dataset Overview**: Shape, types, quality scores (completeness, uniqueness, variability, size adequacy)
- **Target Variable Analysis**: Problem type, class distribution, imbalance
- **Algorithm Recommendations**: Top 5 ranked with scores, reasons, strengths, hyperparameters, libraries
- **Starter Code**: Ready-to-run Python code for the #1 algorithm
- **Preprocessing Pipeline**: Ordered steps with tools and approaches
- **Evaluation Strategy**: Primary metric, validation approach, all metrics
- **Tool Ecosystem**: Libraries for data loading, ML, DL, experiment tracking, deployment
- **Next Steps Checklist**: 10-item actionable checklist

## Algorithm Catalog

The recommender evaluates these algorithm families:

| Family | Algorithms | Best For |
|--------|-----------|----------|
| Linear Models | Logistic Regression, Linear Regression, Ridge, Lasso | Small data, interpretability, baselines |
| Ensemble (Tree) | Random Forest | Medium data, feature importance, robustness |
| Boosting | XGBoost, LightGBM | Tabular data SOTA, Kaggle competitions |
| Kernel Methods | SVM | High-dimensional, small-medium data |
| Instance-Based | KNN | Small data, non-parametric |
| Deep Learning (Tabular) | Neural Networks, TabNet | Large tabular datasets (>10K rows) |
| Deep Learning (NLP) | LSTM/RNN, Transformers (BERT, etc.) | Text classification, generation, similarity |
| Deep Learning (Vision) | CNN (ResNet, EfficientNet) | Image classification, object detection |
| Clustering | K-Means, DBSCAN | Unsupervised segmentation, exploration |
| Anomaly Detection | Isolation Forest, Autoencoder | Fraud detection, outlier detection |

## Multi-Agent Architecture

This workflow is designed for multi-agent orchestration in Claude Code:

```
┌──────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                      │
│  Reads this workflow, decides sequence, handles errors     │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────┐  │
│  │   PROFILER   │──▶│  RECOMMENDER │──▶│   REPORTER   │  │
│  │   AGENT      │   │   AGENT      │   │   AGENT      │  │
│  │              │   │              │   │              │  │
│  │ profile_     │   │ recommend_   │   │ generate_    │  │
│  │ dataset.py   │   │ algorithms.py│   │ training_    │  │
│  │              │   │              │   │ plan.py      │  │
│  └─────────────┘   └──────────────┘   └──────────────┘  │
│         │                  │                  │           │
│         ▼                  ▼                  ▼           │
│   profile.json    recommendations.json  training_plan.md │
│                                                            │
└──────────────────────────────────────────────────────────┘
```

**How agents coordinate:**
1. The **Orchestrator Agent** (Claude) reads this workflow and plans the execution
2. The **Profiler Agent** runs `profile_dataset.py` and validates the output
3. The **Recommender Agent** reads the profile and runs `recommend_algorithms.py`
4. The **Reporter Agent** combines both outputs into the final training plan
5. If any step fails, the Orchestrator reads the error, fixes it, and retries

**For Claude Code multi-agent usage:**
- Use `--worktree` to run parallel analyses on different datasets
- Use Plan Mode (`Shift+Tab`) to review the approach before committing
- Use subagents to delegate each step to a specialized worker

## Edge Cases

| Situation | How to Handle |
|-----------|---------------|
| **No target column specified** | Defaults to unsupervised mode (clustering recommendations) |
| **Dataset too small (<30 rows)** | Warn user; recommend simple models (KNN, Linear) with cross-validation |
| **Dataset too large (>1M rows)** | Recommend sampling first, or suggest LightGBM/Neural Net for full data |
| **All text columns** | Route to NLP recommendations (Transformers, TF-IDF + ML) |
| **All numeric columns** | Route to tabular ML/DL recommendations |
| **Severe class imbalance (>10:1)** | Flag prominently; recommend SMOTE, class_weight, focal loss |
| **>50% missing values** | Flag data quality issue; recommend column dropping + imputation |
| **High multicollinearity** | Recommend PCA or regularization (Ridge/Lasso) |
| **Mixed types (text + numeric)** | Recommend hybrid approach: TF-IDF for text + boosting for tabular |
| **Unsupported file format** | Error with message; suggest conversion to CSV |

## Supported File Formats

| Format | Extension | Library |
|--------|-----------|---------|
| CSV | `.csv` | `pandas.read_csv` |
| JSON | `.json` | `pandas.read_json` |
| Parquet | `.parquet` | `pandas.read_parquet` |
| Excel | `.xls`, `.xlsx` | `pandas.read_excel` |

## Lessons Learned

<!-- Update this section as you discover quirks, limitations, or failure patterns -->
- (none yet — this is a new workflow)
