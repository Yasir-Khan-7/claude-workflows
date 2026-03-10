#!/usr/bin/env python3
"""
Recommend ML/DL algorithms based on a dataset profile.

This is the core intelligence of the ML Data Advisor. It reads the
dataset profile from Step 1 and produces algorithm recommendations
ranked by suitability, with explanations, hyperparameter guidance,
and tool/library suggestions.

Usage:
    python tools/recommend_algorithms.py --profile .tmp/profile.json --output .tmp/recommendations.json

Decision Logic:
    The recommender uses a rule-based scoring system that evaluates:
    1. Problem type (classification, regression, NLP, clustering, etc.)
    2. Dataset size (rows and columns)
    3. Data types present (numeric, categorical, text, mixed)
    4. Data quality (missing values, imbalance, correlations)
    5. Interpretability requirements

    Each algorithm gets a suitability score (0-100) based on how well
    it fits these criteria. The top recommendations are returned with
    explanations for why each algorithm was selected or rejected.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ALGORITHM_CATALOG = {
    "logistic_regression": {
        "name": "Logistic Regression",
        "family": "ml_linear",
        "tasks": ["binary_classification", "multiclass_classification"],
        "strengths": ["Interpretable", "Fast training", "Works with small data", "Good baseline", "Probabilistic outputs"],
        "weaknesses": ["Assumes linear decision boundary", "Poor with complex interactions", "Needs feature engineering"],
        "min_rows": 50,
        "max_cols_ideal": 500,
        "handles_missing": False,
        "handles_categorical": False,
        "needs_scaling": True,
        "interpretable": True,
        "libraries": {"scikit-learn": "sklearn.linear_model.LogisticRegression", "statsmodels": "statsmodels.api.Logit"},
        "hyperparams": {"C": "Regularization strength (try 0.01, 0.1, 1, 10)", "penalty": "l1, l2, or elasticnet", "solver": "lbfgs (default), saga (for l1)"},
    },
    "random_forest": {
        "name": "Random Forest",
        "family": "ml_ensemble",
        "tasks": ["binary_classification", "multiclass_classification", "regression"],
        "strengths": ["Handles non-linear relationships", "Feature importance built-in", "Robust to outliers", "Minimal preprocessing", "Handles missing values (some implementations)"],
        "weaknesses": ["Can overfit on noisy data", "Slow for very large datasets", "Less interpretable than linear models"],
        "min_rows": 100,
        "max_cols_ideal": 2000,
        "handles_missing": False,
        "handles_categorical": False,
        "needs_scaling": False,
        "interpretable": False,
        "libraries": {"scikit-learn": "sklearn.ensemble.RandomForestClassifier / RandomForestRegressor"},
        "hyperparams": {"n_estimators": "100-1000 (start with 200)", "max_depth": "None (auto) or 10-30", "min_samples_leaf": "1-10", "max_features": "sqrt (classification) or 0.33 (regression)"},
    },
    "xgboost": {
        "name": "XGBoost",
        "family": "ml_boosting",
        "tasks": ["binary_classification", "multiclass_classification", "regression"],
        "strengths": ["State-of-the-art tabular performance", "Handles missing values natively", "Built-in regularization", "Feature importance", "GPU support"],
        "weaknesses": ["Many hyperparameters to tune", "Can overfit on small datasets", "Slower than linear models"],
        "min_rows": 200,
        "max_cols_ideal": 5000,
        "handles_missing": True,
        "handles_categorical": True,
        "needs_scaling": False,
        "interpretable": False,
        "libraries": {"xgboost": "xgboost.XGBClassifier / XGBRegressor", "scikit-learn": "Via sklearn API wrapper"},
        "hyperparams": {"n_estimators": "100-1000", "max_depth": "3-10 (start with 6)", "learning_rate": "0.01-0.3 (start with 0.1)", "subsample": "0.7-1.0", "colsample_bytree": "0.7-1.0", "reg_alpha": "0-1 (L1)", "reg_lambda": "0-1 (L2)"},
    },
    "lightgbm": {
        "name": "LightGBM",
        "family": "ml_boosting",
        "tasks": ["binary_classification", "multiclass_classification", "regression"],
        "strengths": ["Faster than XGBoost on large data", "Lower memory usage", "Handles categorical features natively", "Great for high-dimensional data"],
        "weaknesses": ["Can overfit on small datasets (<1000 rows)", "Leaf-wise growth can cause issues", "Sensitive to hyperparameters"],
        "min_rows": 500,
        "max_cols_ideal": 10000,
        "handles_missing": True,
        "handles_categorical": True,
        "needs_scaling": False,
        "interpretable": False,
        "libraries": {"lightgbm": "lightgbm.LGBMClassifier / LGBMRegressor"},
        "hyperparams": {"num_leaves": "31-255", "max_depth": "-1 (auto) or 5-15", "learning_rate": "0.01-0.3", "n_estimators": "100-2000", "min_child_samples": "20-100"},
    },
    "svm": {
        "name": "Support Vector Machine",
        "family": "ml_kernel",
        "tasks": ["binary_classification", "multiclass_classification", "regression"],
        "strengths": ["Effective in high-dimensional space", "Memory efficient (uses support vectors)", "Kernel trick for non-linear boundaries"],
        "weaknesses": ["Slow on large datasets (O(n^2) to O(n^3))", "Sensitive to feature scaling", "No probabilistic output by default", "Poor with noisy overlapping classes"],
        "min_rows": 50,
        "max_cols_ideal": 1000,
        "handles_missing": False,
        "handles_categorical": False,
        "needs_scaling": True,
        "interpretable": False,
        "libraries": {"scikit-learn": "sklearn.svm.SVC / SVR"},
        "hyperparams": {"C": "0.1-100", "kernel": "rbf (default), linear, poly", "gamma": "scale or auto"},
    },
    "knn": {
        "name": "K-Nearest Neighbors",
        "family": "ml_instance",
        "tasks": ["binary_classification", "multiclass_classification", "regression"],
        "strengths": ["Simple and intuitive", "No training phase", "Non-parametric", "Good for small datasets"],
        "weaknesses": ["Very slow prediction on large data", "Curse of dimensionality", "Sensitive to irrelevant features and scale"],
        "min_rows": 30,
        "max_cols_ideal": 50,
        "handles_missing": False,
        "handles_categorical": False,
        "needs_scaling": True,
        "interpretable": True,
        "libraries": {"scikit-learn": "sklearn.neighbors.KNeighborsClassifier / KNeighborsRegressor"},
        "hyperparams": {"n_neighbors": "3-20 (use sqrt(n) as starting point)", "weights": "uniform or distance", "metric": "minkowski (default), manhattan, cosine"},
    },
    "neural_network_tabular": {
        "name": "Neural Network (Tabular)",
        "family": "dl_feedforward",
        "tasks": ["binary_classification", "multiclass_classification", "regression"],
        "strengths": ["Can learn complex non-linear patterns", "Scalable to large datasets", "Flexible architecture"],
        "weaknesses": ["Needs lots of data (>10K rows)", "Hard to interpret", "Requires careful tuning", "Slow training without GPU"],
        "min_rows": 5000,
        "max_cols_ideal": 5000,
        "handles_missing": False,
        "handles_categorical": False,
        "needs_scaling": True,
        "interpretable": False,
        "libraries": {"pytorch": "torch.nn.Sequential", "tensorflow": "tf.keras.Sequential", "pytorch-tabnet": "pytorch_tabnet.TabNetClassifier"},
        "hyperparams": {"hidden_layers": "2-5 layers", "units_per_layer": "64-512", "activation": "ReLU (hidden), sigmoid/softmax (output)", "dropout": "0.1-0.5", "learning_rate": "1e-4 to 1e-2", "batch_size": "32-256", "epochs": "50-500 with early stopping"},
    },
    "lstm_rnn": {
        "name": "LSTM / RNN",
        "family": "dl_recurrent",
        "tasks": ["nlp_classification", "nlp_generation", "time_series_forecasting"],
        "strengths": ["Captures sequential patterns", "Good for variable-length sequences", "Memory over long sequences (LSTM)"],
        "weaknesses": ["Slow to train", "Difficult to parallelize", "Gradient issues on very long sequences", "Largely superseded by Transformers for NLP"],
        "min_rows": 5000,
        "max_cols_ideal": 500,
        "handles_missing": False,
        "handles_categorical": False,
        "needs_scaling": True,
        "interpretable": False,
        "libraries": {"pytorch": "torch.nn.LSTM", "tensorflow": "tf.keras.layers.LSTM"},
        "hyperparams": {"hidden_size": "64-512", "num_layers": "1-3", "dropout": "0.1-0.5", "bidirectional": "True for classification, False for generation", "learning_rate": "1e-4 to 1e-3"},
    },
    "transformer": {
        "name": "Transformer / Pre-trained LLM",
        "family": "dl_transformer",
        "tasks": ["nlp_classification", "nlp_generation", "text_similarity"],
        "strengths": ["State-of-the-art NLP performance", "Transfer learning from massive corpora", "Handles long-range dependencies", "Fine-tuning is efficient"],
        "weaknesses": ["Very large model size", "Needs GPU", "Can be overkill for simple text tasks", "Expensive to train from scratch"],
        "min_rows": 1000,
        "max_cols_ideal": 100,
        "handles_missing": False,
        "handles_categorical": False,
        "needs_scaling": False,
        "interpretable": False,
        "libraries": {"huggingface": "transformers.AutoModelForSequenceClassification", "pytorch": "torch.nn.Transformer", "openai": "Fine-tuning API"},
        "hyperparams": {"model_name": "bert-base-uncased, roberta-base, distilbert", "learning_rate": "2e-5 to 5e-5", "epochs": "2-5 for fine-tuning", "batch_size": "8-32", "max_length": "128-512 tokens"},
    },
    "cnn_image": {
        "name": "CNN (Convolutional Neural Network)",
        "family": "dl_convolutional",
        "tasks": ["image_classification", "object_detection"],
        "strengths": ["Excellent for spatial/image data", "Transfer learning with pre-trained models", "Translation invariance"],
        "weaknesses": ["Needs lots of image data", "GPU required", "Fixed input size"],
        "min_rows": 1000,
        "max_cols_ideal": 100,
        "handles_missing": False,
        "handles_categorical": False,
        "needs_scaling": True,
        "interpretable": False,
        "libraries": {"pytorch": "torchvision.models (ResNet, EfficientNet)", "tensorflow": "tf.keras.applications", "fastai": "fastai.vision"},
        "hyperparams": {"backbone": "ResNet50, EfficientNetB0, ViT", "learning_rate": "1e-4 to 1e-3", "augmentation": "RandomCrop, HorizontalFlip, ColorJitter", "batch_size": "16-64", "epochs": "10-100 with early stopping"},
    },
    "kmeans": {
        "name": "K-Means Clustering",
        "family": "ml_clustering",
        "tasks": ["clustering"],
        "strengths": ["Simple and fast", "Scales well", "Easy to interpret cluster centroids"],
        "weaknesses": ["Must specify K upfront", "Assumes spherical clusters", "Sensitive to initialization and outliers"],
        "min_rows": 50,
        "max_cols_ideal": 500,
        "handles_missing": False,
        "handles_categorical": False,
        "needs_scaling": True,
        "interpretable": True,
        "libraries": {"scikit-learn": "sklearn.cluster.KMeans"},
        "hyperparams": {"n_clusters": "Use elbow method or silhouette score", "init": "k-means++", "n_init": "10-20", "max_iter": "300"},
    },
    "dbscan": {
        "name": "DBSCAN",
        "family": "ml_clustering",
        "tasks": ["clustering", "anomaly_detection"],
        "strengths": ["No need to specify K", "Finds arbitrary-shaped clusters", "Identifies outliers as noise"],
        "weaknesses": ["Sensitive to eps and min_samples", "Struggles with varying density", "Not great for high dimensions"],
        "min_rows": 50,
        "max_cols_ideal": 100,
        "handles_missing": False,
        "handles_categorical": False,
        "needs_scaling": True,
        "interpretable": True,
        "libraries": {"scikit-learn": "sklearn.cluster.DBSCAN"},
        "hyperparams": {"eps": "Use k-distance plot to determine", "min_samples": "2 * n_features (heuristic)", "metric": "euclidean (default)"},
    },
    "isolation_forest": {
        "name": "Isolation Forest",
        "family": "ml_anomaly",
        "tasks": ["anomaly_detection"],
        "strengths": ["Efficient for anomaly detection", "Scales linearly", "Works well in high dimensions", "No distance computation"],
        "weaknesses": ["Not suitable for classification/regression", "Hard to tune contamination parameter", "Assumes anomalies are few and different"],
        "min_rows": 100,
        "max_cols_ideal": 1000,
        "handles_missing": False,
        "handles_categorical": False,
        "needs_scaling": False,
        "interpretable": False,
        "libraries": {"scikit-learn": "sklearn.ensemble.IsolationForest"},
        "hyperparams": {"n_estimators": "100-300", "contamination": "auto or estimated anomaly fraction", "max_samples": "auto or 256"},
    },
    "autoencoder": {
        "name": "Autoencoder",
        "family": "dl_generative",
        "tasks": ["anomaly_detection", "dimensionality_reduction", "feature_learning"],
        "strengths": ["Learns compressed representations", "Good for anomaly detection via reconstruction error", "Flexible architecture"],
        "weaknesses": ["Needs large datasets", "Hard to train", "Black box"],
        "min_rows": 5000,
        "max_cols_ideal": 5000,
        "handles_missing": False,
        "handles_categorical": False,
        "needs_scaling": True,
        "interpretable": False,
        "libraries": {"pytorch": "Custom encoder-decoder architecture", "tensorflow": "tf.keras (encoder + decoder layers)"},
        "hyperparams": {"encoding_dim": "Original dim / 4 to / 10", "hidden_layers": "2-4 symmetric layers", "activation": "ReLU (hidden), sigmoid (output)", "learning_rate": "1e-4 to 1e-3"},
    },
    "linear_regression": {
        "name": "Linear Regression",
        "family": "ml_linear",
        "tasks": ["regression"],
        "strengths": ["Highly interpretable", "Fast", "Good baseline", "Statistical inference built in"],
        "weaknesses": ["Assumes linearity", "Sensitive to outliers", "Multicollinearity issues"],
        "min_rows": 30,
        "max_cols_ideal": 500,
        "handles_missing": False,
        "handles_categorical": False,
        "needs_scaling": True,
        "interpretable": True,
        "libraries": {"scikit-learn": "sklearn.linear_model.LinearRegression / Ridge / Lasso", "statsmodels": "statsmodels.api.OLS"},
        "hyperparams": {"alpha": "Regularization strength (Ridge/Lasso: 0.01-100)", "fit_intercept": "True (default)"},
    },
}


def _infer_problem_type(profile: dict) -> dict:
    """Infer the ML problem type from the dataset profile."""
    target = profile.get("target_analysis")

    if target and target.get("problem_type"):
        return {
            "problem_type": target["problem_type"],
            "confidence": "high",
            "source": "target_column_analysis",
        }

    type_summary = profile.get("type_summary", {})
    has_text = type_summary.get("text", 0) > 0
    n_rows = profile["shape"]["rows"]

    if has_text and type_summary.get("text", 0) >= profile["shape"]["columns"] * 0.3:
        return {
            "problem_type": "nlp_classification",
            "confidence": "medium",
            "source": "inferred_from_text_columns",
            "note": "High proportion of text columns suggests NLP task. Specify --target to clarify.",
        }

    return {
        "problem_type": "clustering",
        "confidence": "low",
        "source": "no_target_specified",
        "note": "No target column specified. Defaulting to unsupervised (clustering). Use --target to specify a supervised task.",
    }


def _score_algorithm(algo: dict, profile: dict, problem: dict) -> dict:
    """Score an algorithm against the dataset profile. Returns score and reasoning."""
    problem_type = problem["problem_type"]
    n_rows = profile["shape"]["rows"]
    n_cols = profile["shape"]["columns"]
    type_summary = profile.get("type_summary", {})
    quality = profile.get("quality_score", {})

    if problem_type not in algo["tasks"]:
        return {"score": 0, "reasons": ["Does not support this problem type"], "selected": False}

    score = 50
    reasons = []

    if n_rows >= algo["min_rows"]:
        if n_rows >= algo["min_rows"] * 10:
            score += 15
            reasons.append(f"Ample data ({n_rows} rows >> {algo['min_rows']} minimum)")
        else:
            score += 5
            reasons.append(f"Sufficient data ({n_rows} rows >= {algo['min_rows']} minimum)")
    else:
        score -= 30
        reasons.append(f"Insufficient data ({n_rows} rows < {algo['min_rows']} minimum)")

    if n_cols <= algo["max_cols_ideal"]:
        score += 5
    elif n_cols > algo["max_cols_ideal"] * 2:
        score -= 10
        reasons.append(f"Very high dimensionality ({n_cols} cols) may degrade performance")

    has_missing = quality.get("completeness", 100) < 95
    if has_missing and algo["handles_missing"]:
        score += 10
        reasons.append("Handles missing values natively")
    elif has_missing and not algo["handles_missing"]:
        score -= 5
        reasons.append("Requires imputation for missing values")

    has_categorical = type_summary.get("categorical", 0) > 0
    if has_categorical and algo["handles_categorical"]:
        score += 5
        reasons.append("Handles categorical features natively")
    elif has_categorical and not algo["handles_categorical"]:
        score -= 3
        reasons.append("Requires encoding for categorical features")

    target = profile.get("target_analysis", {})
    if target.get("is_imbalanced") and algo["family"] in ("ml_boosting", "ml_ensemble"):
        score += 10
        reasons.append("Handles class imbalance well with sample_weight or scale_pos_weight")
    elif target.get("is_imbalanced") and algo["family"] in ("ml_linear", "ml_instance"):
        score -= 5
        reasons.append("May struggle with class imbalance without resampling")

    if algo["family"] == "ml_boosting" and n_rows >= 500:
        score += 10
        reasons.append("Gradient boosting excels on tabular data")
    elif algo["family"] == "dl_transformer" and type_summary.get("text", 0) > 0:
        score += 15
        reasons.append("Transformers are state-of-the-art for NLP tasks")
    elif algo["family"] in ("dl_feedforward", "dl_recurrent") and n_rows < 5000:
        score -= 15
        reasons.append("Deep learning typically needs >5K rows to outperform ML")

    high_corr = profile.get("high_correlations", [])
    if len(high_corr) > 3 and algo["family"] == "ml_linear":
        score -= 10
        reasons.append("High multicollinearity detected; consider regularized variant (Ridge/Lasso)")

    score = max(0, min(100, score))

    return {
        "score": score,
        "reasons": reasons,
        "selected": score >= 40,
    }


def recommend_algorithms(profile: dict) -> dict:
    """
    Generate algorithm recommendations based on dataset profile.

    Args:
        profile: Output from profile_dataset tool.

    Returns:
        Dict with problem type, ranked recommendations, and preprocessing advice.
    """
    problem = _infer_problem_type(profile)
    n_rows = profile["shape"]["rows"]
    n_cols = profile["shape"]["columns"]
    type_summary = profile.get("type_summary", {})
    quality = profile.get("quality_score", {})

    scored = []
    for algo_id, algo in ALGORITHM_CATALOG.items():
        result = _score_algorithm(algo, profile, problem)
        if result["selected"]:
            scored.append({
                "algorithm_id": algo_id,
                "name": algo["name"],
                "family": algo["family"],
                "suitability_score": result["score"],
                "reasons": result["reasons"],
                "strengths": algo["strengths"],
                "weaknesses": algo["weaknesses"],
                "libraries": algo["libraries"],
                "hyperparameters": algo["hyperparams"],
                "needs_scaling": algo["needs_scaling"],
                "interpretable": algo["interpretable"],
            })

    scored.sort(key=lambda x: x["suitability_score"], reverse=True)

    preprocessing = []
    if quality.get("completeness", 100) < 95:
        missing_pct = round(100 - quality.get("completeness", 100), 1)
        preprocessing.append({
            "step": "Handle Missing Values",
            "reason": f"{missing_pct}% of cells have missing values",
            "approaches": [
                "Numeric: median imputation (robust to outliers) or KNN imputation",
                "Categorical: mode imputation or 'missing' category",
                "If >40% missing in a column, consider dropping it",
            ],
            "tools": ["sklearn.impute.SimpleImputer", "sklearn.impute.KNNImputer"],
        })

    if type_summary.get("categorical", 0) > 0:
        preprocessing.append({
            "step": "Encode Categorical Features",
            "reason": f"{type_summary.get('categorical', 0)} categorical columns detected",
            "approaches": [
                "Low cardinality (<10 values): One-Hot Encoding",
                "High cardinality (>10 values): Target Encoding or Ordinal Encoding",
                "For tree-based models: LightGBM handles categoricals natively",
            ],
            "tools": ["sklearn.preprocessing.OneHotEncoder", "sklearn.preprocessing.OrdinalEncoder", "category_encoders.TargetEncoder"],
        })

    needs_scaling_algos = [a for a in scored if a["needs_scaling"]]
    if needs_scaling_algos:
        preprocessing.append({
            "step": "Feature Scaling",
            "reason": f"Required by: {', '.join(a['name'] for a in needs_scaling_algos[:3])}",
            "approaches": [
                "StandardScaler: zero mean, unit variance (good default)",
                "MinMaxScaler: scale to [0, 1] (if distribution is not Gaussian)",
                "RobustScaler: uses median/IQR (robust to outliers)",
            ],
            "tools": ["sklearn.preprocessing.StandardScaler", "sklearn.preprocessing.RobustScaler"],
        })

    if type_summary.get("text", 0) > 0:
        preprocessing.append({
            "step": "Text Preprocessing",
            "reason": f"{type_summary.get('text', 0)} text columns detected",
            "approaches": [
                "For classical ML: TF-IDF vectorization",
                "For deep learning: tokenization with pre-trained tokenizer (BERT, etc.)",
                "Common: lowercase, remove stopwords, lemmatize (for TF-IDF path)",
            ],
            "tools": ["sklearn.feature_extraction.text.TfidfVectorizer", "transformers.AutoTokenizer", "nltk", "spacy"],
        })

    high_corr = profile.get("high_correlations", [])
    if len(high_corr) > 0:
        preprocessing.append({
            "step": "Handle Correlated Features",
            "reason": f"{len(high_corr)} highly correlated feature pairs found",
            "approaches": [
                "Drop one feature from each highly correlated pair",
                "Use PCA for dimensionality reduction",
                "Tree-based models are generally robust to correlation",
            ],
            "tools": ["sklearn.decomposition.PCA", "sklearn.feature_selection.VarianceThreshold"],
        })

    target = profile.get("target_analysis", {})
    if target.get("is_imbalanced"):
        preprocessing.append({
            "step": "Handle Class Imbalance",
            "reason": f"Imbalance ratio: {target.get('imbalance_ratio', 'unknown')}:1",
            "approaches": [
                "SMOTE: Synthetic Minority Over-sampling",
                "Class weights: Pass sample_weight or class_weight='balanced'",
                "Undersampling majority class (if data is abundant)",
                "Focal loss (for deep learning)",
            ],
            "tools": ["imblearn.over_sampling.SMOTE", "sklearn class_weight parameter"],
        })

    approach = "ml"
    approach_reason = ""
    if problem["problem_type"] in ("nlp_classification", "nlp_generation", "text_similarity"):
        approach = "dl"
        approach_reason = "Text/NLP tasks benefit most from deep learning (Transformers)"
    elif problem["problem_type"] in ("image_classification", "object_detection"):
        approach = "dl"
        approach_reason = "Image tasks require deep learning (CNNs/Vision Transformers)"
    elif n_rows >= 50000 and n_cols >= 100:
        approach = "dl"
        approach_reason = f"Large dataset ({n_rows} rows, {n_cols} cols) where deep learning can shine"
    elif n_rows < 5000:
        approach = "ml"
        approach_reason = f"Small dataset ({n_rows} rows) — classical ML is more data-efficient"
    else:
        approach = "ml_first"
        approach_reason = f"Medium dataset ({n_rows} rows) — start with ML, try DL if ML plateaus"

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "problem_type": problem,
        "recommended_approach": {
            "approach": approach,
            "reason": approach_reason,
            "explanation": {
                "ml": "Classical Machine Learning: Random Forest, XGBoost, LightGBM, etc. Best when data < 50K rows, features are tabular, and interpretability matters.",
                "dl": "Deep Learning: Neural networks, Transformers, CNNs. Best for unstructured data (text, images), very large datasets, or when accuracy > interpretability.",
                "ml_first": "Start with ML for faster iteration, then explore DL if performance plateaus. This is the most pragmatic approach for medium-sized tabular datasets.",
            }[approach],
        },
        "recommendations": scored[:8],
        "preprocessing_steps": preprocessing,
        "evaluation_strategy": _suggest_evaluation(problem, profile),
    }


def _suggest_evaluation(problem: dict, profile: dict) -> dict:
    """Suggest evaluation metrics and validation strategy."""
    problem_type = problem["problem_type"]
    n_rows = profile["shape"]["rows"]
    target = profile.get("target_analysis", {})

    if problem_type == "binary_classification":
        metrics = ["AUC-ROC (primary)", "F1 Score", "Precision", "Recall", "Accuracy"]
        if target.get("is_imbalanced"):
            metrics = ["AUC-ROC (primary)", "F1 Score (macro)", "Precision-Recall AUC", "Matthews Correlation Coefficient"]
    elif problem_type == "multiclass_classification":
        metrics = ["F1 Score (macro)", "Accuracy", "Confusion Matrix", "Classification Report"]
    elif problem_type == "regression":
        metrics = ["RMSE (primary)", "MAE", "R-squared", "MAPE"]
    elif problem_type in ("nlp_classification",):
        metrics = ["F1 Score (macro)", "Accuracy", "Confusion Matrix"]
    elif problem_type == "clustering":
        metrics = ["Silhouette Score", "Calinski-Harabasz Index", "Davies-Bouldin Index", "Elbow Method (for K)"]
    elif problem_type == "anomaly_detection":
        metrics = ["Precision@K", "Recall@K", "F1 at threshold", "AUC-ROC (if labels available)"]
    else:
        metrics = ["Task-specific metric TBD"]

    if n_rows < 1000:
        validation = "Stratified K-Fold (k=5 or k=10) — small dataset, need robust estimate"
    elif n_rows < 50000:
        validation = "Stratified K-Fold (k=5) or Train/Validation/Test split (70/15/15)"
    else:
        validation = "Train/Validation/Test split (80/10/10) — large data, single split is sufficient"

    return {
        "metrics": metrics,
        "primary_metric": metrics[0] if metrics else "TBD",
        "validation_strategy": validation,
        "tools": ["sklearn.model_selection.cross_val_score", "sklearn.model_selection.StratifiedKFold", "sklearn.metrics"],
    }


def main():
    parser = argparse.ArgumentParser(description="Recommend ML/DL algorithms based on dataset profile")
    parser.add_argument("--profile", required=True, help="Path to dataset profile JSON (from profile_dataset)")
    parser.add_argument("--output", required=True, help="Path to write recommendations JSON")
    args = parser.parse_args()

    with open(args.profile, encoding="utf-8") as f:
        profile = json.load(f)

    print(f"Generating recommendations for: {profile.get('file', 'unknown')}")
    print(f"  Shape: {profile['shape']['rows']} x {profile['shape']['columns']}")

    recommendations = recommend_algorithms(profile)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(recommendations, f, indent=2, ensure_ascii=False)

    approach = recommendations["recommended_approach"]
    print(f"\n  Problem Type: {recommendations['problem_type']['problem_type']}")
    print(f"  Recommended Approach: {approach['approach'].upper()}")
    print(f"  Reason: {approach['reason']}")

    print(f"\n  Top Algorithms:")
    for i, rec in enumerate(recommendations["recommendations"][:5], 1):
        print(f"    {i}. {rec['name']} (score: {rec['suitability_score']})")

    print(f"\n  Preprocessing Steps: {len(recommendations['preprocessing_steps'])}")
    for step in recommendations["preprocessing_steps"]:
        print(f"    - {step['step']}: {step['reason']}")

    print(f"\nRecommendations saved to {args.output}")


if __name__ == "__main__":
    main()
