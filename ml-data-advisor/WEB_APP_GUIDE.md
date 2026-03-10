# ML Data Advisor - Web App Setup Guide

## What Was Built

A complete web application for the ML Data Advisor with:
- **FastAPI Backend** (`web/app.py`) - Wraps the existing CLI tools into REST API endpoints
- **Modern Frontend** (`web/static/index.html`) - Beautiful dark-themed single-page app
- **Groq Integration** - Optional AI-powered deep analysis using Groq LLM API
- **Full Pipeline** - Upload → Profile → Recommend → Report generation in <1 second

## Quick Start

### 1. Install Dependencies

```bash
cd ml-data-advisor
pip install -r requirements.txt
```

**New dependencies added:**
- `fastapi>=0.115.0`
- `uvicorn>=0.34.0`
- `python-multipart>=0.0.18`

### 2. Start the Server

```bash
uvicorn web.app:app --reload --port 8000
```

The app will be available at: **http://localhost:8000**

### 3. Use the Web Interface

1. **Upload Dataset** - Drag & drop or click to browse (CSV, JSON, Parquet, Excel)
2. **Target Column** (optional) - Enter your target variable name (e.g., `default`, `price`, `churn`)
3. **Groq API Key** (optional) - Get a free key at https://console.groq.com/keys for AI-powered insights
4. **Analyze** - Click the button and get results in ~0.03 seconds

### 4. View Results

The interface has 5 tabs:
- **Overview** - Data quality, target analysis, column types
- **Algorithms** - Top 5 ranked recommendations with scores
- **Preprocessing** - Step-by-step preprocessing pipeline
- **AI Insights** - Groq-powered deep analysis (if API key provided)
- **Full Report** - Complete training plan markdown

## API Endpoint

### POST `/api/analyze`

```bash
curl -X POST http://localhost:8000/api/analyze \
  -F "file=@your_data.csv" \
  -F "target=label_column" \
  -F "groq_key=gsk_xxxxxxxx"
```

**Response:**
```json
{
  "success": true,
  "elapsed_seconds": 0.03,
  "profile": {...},
  "recommendations": {...},
  "report_markdown": "...",
  "groq_insights": {...}
}
```

## Features

### Core Analysis (No API Key Required)
- Dataset profiling (types, stats, quality score, correlations)
- Algorithm recommendations (15+ algorithms with scoring)
- ML vs DL decision logic
- Preprocessing pipeline generation
- Full training plan with code snippets
- Evaluation strategy and metrics

### AI-Powered Deep Analysis (Groq API Key Optional)
When you provide a Groq API key, you get additional insights:
- **Quick Assessment** - Is the data ML-ready? Any red flags?
- **Strategy Recommendation** - What would a senior ML engineer do?
- **Common Pitfalls** - Dataset-specific mistakes to avoid
- **Quick Win** - Fastest path to a baseline model
- **Advanced Tip** - Performance optimization ideas

Powered by `llama-3.3-70b-versatile` via Groq Cloud.

## Testing

The API has been tested with the `loan_default_dataset.csv` (5,025 rows, 13 columns):
- ✅ Analysis completes in 0.03 seconds
- ✅ Correctly detects binary classification
- ✅ Recommends ML-first approach
- ✅ Top algorithm: XGBoost (95/100 score)
- ✅ Detects class imbalance (4.53:1 ratio)
- ✅ Generates 10KB+ training plan report
- ✅ JSON serialization works with numpy types

## Architecture

```
FastAPI Backend (web/app.py)
    │
    ├── POST /api/analyze
    │   ├── profile_dataset() ────────────> profile.json
    │   ├── recommend_algorithms() ───────> recommendations.json
    │   ├── generate_report() ───────────> training_plan.md
    │   └── _call_groq_analysis() ───────> groq_insights (optional)
    │
    └── GET / ──────────────────────────> index.html

Frontend (web/static/index.html)
    │
    ├── Drag & Drop File Upload
    ├── Target Column Input
    ├── Groq API Key Input
    ├── Analysis Button
    │
    └── Results Display
        ├── Stats Cards (rows, problem type, approach, quality)
        ├── Tab 1: Overview (quality bars, target analysis, column types)
        ├── Tab 2: Algorithms (ranked list with scores and reasoning)
        ├── Tab 3: Preprocessing (ordered pipeline with tools)
        ├── Tab 4: AI Insights (Groq-powered deep analysis)
        └── Tab 5: Full Report (complete training plan markdown)
```

## Deployment

### Local Development
```bash
uvicorn web.app:app --reload --port 8000
```

### Production
```bash
uvicorn web.app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker (Create a Dockerfile)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Git Push Success

Your code has been successfully pushed to GitHub:
```
Repository: git@github.com:Yasir-Khan-7/claude-workflows.git
Commit: "added ML-data-advisor workflow"
Files: 12 new files, 3083 insertions
```

## What's Included

```
ml-data-advisor/
├── tools/
│   ├── profile_dataset.py          # Dataset profiler
│   ├── recommend_algorithms.py     # Algorithm recommender
│   ├── generate_training_plan.py   # Report generator
│   └── run_advisor.py              # CLI orchestrator
├── web/
│   ├── app.py                      # FastAPI backend
│   └── static/
│       └── index.html              # Frontend UI
├── workflows/
│   └── analyze_data.md             # WAT workflow SOP
├── tests/
│   └── test_pipeline.py            # 44 tests (all passing)
├── requirements.txt                # Python dependencies
└── README.md                       # Documentation
```

## Next Steps

1. **Try it locally**: `cd ml-data-advisor && uvicorn web.app:app --reload`
2. **Get a Groq key** (optional): https://console.groq.com/keys (free tier available)
3. **Upload your dataset** and see the recommendations
4. **Share the tool** with your team or deploy it to a server

Enjoy your new ML Data Advisor web app! 🚀
