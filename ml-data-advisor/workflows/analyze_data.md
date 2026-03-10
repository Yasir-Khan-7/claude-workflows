# Workflow: ML/DL Data Advisor

## Objective
Analyze a dataset provided by an AI/ML engineer using an **LLM-powered agent** that dynamically reasons about the data — determining whether Machine Learning or Deep Learning is the best fit, recommending specific algorithms ranked by suitability, generating preprocessing guidance, and producing a comprehensive training plan.

This workflow follows the **WAT Framework** architecture:
- **Tools** handle deterministic execution (data profiling, report generation)
- **Agent** (LLM) handles intelligent reasoning (algorithm selection, strategy, preprocessing)
- **Workflow** (this file) defines the SOP

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
| Groq API key (required) | User provides | `gsk_xxx...` — powers the LLM Agent |
| File format | Auto-detected | CSV, JSON, Parquet, Excel |

**API key is required.** The LLM Agent dynamically reasons about the data, producing tailored recommendations with starter code. Get a free key at https://console.groq.com/keys

## Tools Used

| Tool | Layer | Purpose |
|------|-------|---------|
| `tools/profile_dataset.py` | **Tool** (deterministic) | Profile the dataset: detect types, compute stats, assess quality, analyze target |
| `tools/llm_advisor.py` | **Agent** (LLM-powered) | Send profile to LLM; get dynamic algorithm recommendations, preprocessing, strategy, and insights |
| `tools/generate_training_plan.py` | **Tool** (deterministic) | Compile everything into a structured Markdown report with code snippets |
| `tools/run_advisor.py` | **Orchestrator** | Runs all steps in sequence |

## Procedure

### Step 1: Profile the Dataset (Tool — Deterministic)

```bash
python tools/profile_dataset.py --input data.csv --target label_column --output .tmp/ml_advisor/profile.json
```

This is a **deterministic tool** — same input always produces the same output:
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

### Step 2: Generate Algorithm Recommendations (Agent — LLM-Powered)

```python
from llm_advisor import get_llm_recommendations
recommendations = get_llm_recommendations(profile, api_key="gsk_xxx")
```

The LLM Agent receives the full profile and **reasons dynamically** about:
- Problem type classification with confidence and explanation
- Algorithm ranking with suitability scores specific to THIS dataset
- Why each algorithm fits or doesn't fit (not hardcoded rules)
- Preprocessing pipeline ordered by priority
- Evaluation strategy tailored to the problem
- Deep analysis: quick assessment, strategy, pitfalls, quick wins, advanced tips
- Starter code for each recommended algorithm

**Why the Agent layer matters:** A static catalog can't reason about the interaction between features, domain context, or edge cases. The LLM agent sees the full profile and applies ML engineering expertise dynamically — the same way a senior data scientist would analyze the data before choosing an approach.

### Step 3: Generate Training Plan Report (Tool — Deterministic)

```bash
python tools/generate_training_plan.py --profile .tmp/ml_advisor/profile.json --recommendations .tmp/ml_advisor/recommendations.json --output .tmp/ml_advisor/training_plan.md
```

- Reads both the profile and recommendations (from either agent or fallback)
- Generates a comprehensive Markdown report
- This is a formatting tool — it doesn't make decisions

### One-Shot: Run Full Pipeline

```bash
python tools/run_advisor.py --input data.csv --target label_column
```

This runs all three steps in sequence and produces all output files.

### Web Interface

```bash
cd ml-data-advisor
uvicorn web.app:app --reload --port 8000
```

The web app at `http://localhost:8000` provides:
- File upload with drag-and-drop
- Target column and API key inputs
- Interactive results dashboard with tabs (Overview, Algorithms, Preprocessing, AI Agent, Full Report)
- Real-time analysis mode indicator (AI Agent vs Rule-Based)

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

## WAT Architecture

This workflow implements the WAT (Workflows, Agents, Tools) framework:

```
┌──────────────────────────────────────────────────────────────┐
│                     WORKFLOW (this file)                       │
│  Defines the SOP, inputs, outputs, and error handling         │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─────────────┐   ┌───────────────────┐   ┌──────────────┐  │
│  │    TOOL      │   │      AGENT        │   │     TOOL     │  │
│  │ Deterministic│──▶│   LLM-Powered     │──▶│ Deterministic│  │
│  │              │   │                   │   │              │  │
│  │ profile_     │   │ llm_advisor.py    │   │ generate_    │  │
│  │ dataset.py   │   │ (Groq GPT-OSS)   │   │ training_    │  │
│  │              │   │                   │   │ plan.py      │  │
│  │ Extracts     │   │ Reasons about     │   │ Formats      │  │
│  │ structured   │   │ algorithms,       │   │ results into │  │
│  │ profile      │   │ preprocessing,    │   │ Markdown     │  │
│  │              │   │ strategy, code    │   │ report       │  │
│  └─────────────┘   └───────────────────┘   └──────────────┘  │
│         │                    │                     │           │
│         ▼                    ▼                     ▼           │
│   profile.json      recommendations.json    training_plan.md  │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

**How the layers work together:**
1. **Tool** (`profile_dataset.py`) deterministically extracts structured metadata from the dataset
2. **Agent** (`llm_advisor.py`) receives the profile and applies ML engineering reasoning via LLM
3. **Tool** (`generate_training_plan.py`) deterministically formats the results into a readable report

**Why this separation matters (from CLAUDE.md):**
> When AI tries to handle every step directly, accuracy drops fast. If each step is 90% accurate, you're down to 59% success after just five steps.

By making profiling and formatting deterministic (100% consistent), and letting the LLM focus solely on reasoning (where it excels), the pipeline stays reliable and intelligent.

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

- **v1.0:** Rule-based recommender returned 0 algorithms for small datasets (<50 rows) due to rigid `min_rows` thresholds.
- **v1.0:** Integer columns with large ranges (e.g., price: 200K-600K) were misclassified as `categorical_numeric` on small datasets because `nunique < 20` was too simplistic.
- **v1.0:** FastAPI couldn't serialize numpy types. Fixed with a `_sanitize()` helper that recursively converts numpy to native Python.
- **v2.0:** The entire recommendation engine was hardcoded rules — ~600 lines of static logic. This violated the WAT principle of "probabilistic AI handles reasoning." Replaced with LLM agent that dynamically reasons about each dataset.
- **v2.0:** Groq `openai/gpt-oss-120b` (500 tps) with `response_format: json_object` reliably returns structured recommendations. Temperature 0.3 balances consistency with creative insight.
- **v2.0:** API key is required — no fallback to hardcoded rules. The WAT framework means AI handles reasoning; if there's no AI, there's no reasoning. Users must provide an LLM to power the agent.
