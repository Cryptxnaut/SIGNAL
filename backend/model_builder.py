"""Model builder — dataset-aware model selection and training."""
import time
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import lightgbm as lgb
import shap

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    r2_score, mean_absolute_error, mean_squared_error,
    f1_score, roc_auc_score, average_precision_score,
    accuracy_score
)
from sklearn.preprocessing import LabelEncoder


def _select_target(df: pd.DataFrame, schema: dict, intent: str) -> str | None:
    """Select target column: highest variance numeric, avoiding ID-like columns."""
    num_cols = [
        c for c, m in schema.get("columns", {}).items()
        if m.get("dtype") == "numeric"
        and c in df.columns
        and not any(kw in c.lower() for kw in ["id", "index", "key", "_id"])
    ]
    if not num_cols:
        return None
    # Score by variance (normalised) + intent keyword match
    intent_lower = intent.lower()
    def score(col):
        v = float(df[col].std() or 0)
        keyword_boost = 2.0 if any(w in col.lower() for w in intent_lower.split()) else 0.0
        return v + keyword_boost
    return max(num_cols, key=score)


def _add_lag_features(df: pd.DataFrame, feature_cols: list[str], n_lags: int = 3) -> pd.DataFrame:
    """Add lag features for time-series data."""
    out = df.copy()
    for col in feature_cols[:4]:  # limit to top 4 cols to avoid explosion
        for lag in range(1, n_lags + 1):
            out[f"{col}_lag{lag}"] = out[col].shift(lag)
    return out.dropna()


def _encode_categoricals(df: pd.DataFrame, schema: dict, feature_cols: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """Target-encode or label-encode categorical columns."""
    out = df.copy()
    new_cols = list(feature_cols)
    for col, meta in schema.get("columns", {}).items():
        if meta.get("dtype") == "categorical" and col in df.columns and col not in feature_cols:
            le = LabelEncoder()
            try:
                out[f"{col}_enc"] = le.fit_transform(out[col].astype(str))
                new_cols.append(f"{col}_enc")
            except Exception:
                pass
    return out, new_cols


def build_model(df: pd.DataFrame, schema: dict, intent: str, depth: str) -> dict:
    t0 = time.time()

    # ── feature/target selection ──────────────────────────────────────────────
    num_cols = [
        c for c, m in schema.get("columns", {}).items()
        if m.get("dtype") == "numeric" and c in df.columns
        and not any(kw in c.lower() for kw in ["id", "index", "key"])
    ]
    if len(num_cols) < 2:
        return {}

    target_col = _select_target(df, schema, intent)
    if not target_col:
        return {}

    feature_cols = [c for c in num_cols if c != target_col]
    if not feature_cols:
        return {}

    # ── detect problem type ───────────────────────────────────────────────────
    target_series = df[target_col].dropna()
    unique_vals = target_series.nunique()
    val_set = set(target_series.unique())

    is_binary = unique_vals == 2 and val_set.issubset({0, 1, 0.0, 1.0, True, False})
    is_multiclass = (not is_binary) and unique_vals <= 15 and unique_vals >= 3 and target_series.dtype in [int, "int64", "int32"]
    is_classification = is_binary or is_multiclass
    problem_type = "binary" if is_binary else "multiclass" if is_multiclass else "regression"

    # ── time series detection → add lag features ───────────────────────────────
    is_ts = schema.get("n_time_series", 0) > 0
    shuffle = not is_ts

    work_df = df[[target_col] + feature_cols].copy()

    if is_ts:
        work_df = _add_lag_features(work_df, feature_cols, n_lags=3)
        # Update feature_cols to include lag columns
        feature_cols = [c for c in work_df.columns if c != target_col]

    work_df = work_df.dropna(subset=[target_col])
    if len(work_df) < 20:
        return {}

    # ── large dataset subsampling ─────────────────────────────────────────────
    MAX_TRAIN_ROWS = 20_000
    if len(work_df) > MAX_TRAIN_ROWS:
        if is_classification:
            # Stratified sample
            work_df = work_df.groupby(target_col, group_keys=False).apply(
                lambda x: x.sample(min(len(x), MAX_TRAIN_ROWS // unique_vals), random_state=42)
            )
        else:
            work_df = work_df.sample(MAX_TRAIN_ROWS, random_state=42)
            if is_ts:
                work_df = work_df.sort_index()

    X = work_df[feature_cols].values
    y = work_df[target_col].values

    if is_multiclass:
        le = LabelEncoder()
        y = le.fit_transform(y)

    # ── train/test split ──────────────────────────────────────────────────────
    test_size = max(0.1, min(0.2, 50 / len(X)))
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, shuffle=shuffle, random_state=42
    )

    # ── model configuration ───────────────────────────────────────────────────
    n_estimators = 100 if depth == "quick" else 500
    common_params = dict(
        n_estimators=n_estimators,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )

    if problem_type == "binary":
        model = lgb.LGBMClassifier(
            objective="binary",
            metric="auc",
            is_unbalance=True,
            **common_params
        )
    elif problem_type == "multiclass":
        model = lgb.LGBMClassifier(
            objective="multiclass",
            num_class=len(np.unique(y)),
            metric="multi_logloss",
            **common_params
        )
    else:
        model = lgb.LGBMRegressor(
            objective="regression_l1",  # MAE-based, more robust than MSE
            metric="mae",
            **common_params
        )

    # ── train ─────────────────────────────────────────────────────────────────
    callbacks = [lgb.early_stopping(50, verbose=False), lgb.log_evaluation(-1)]
    try:
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            callbacks=callbacks,
        )
    except Exception:
        model.fit(X_train, y_train)

    # ── metrics ───────────────────────────────────────────────────────────────
    y_pred = model.predict(X_test)

    if problem_type == "binary":
        y_prob = model.predict_proba(X_test)[:, 1]
        metric_name = "AUC-ROC"
        metric_value = round(float(roc_auc_score(y_test, y_prob)), 4)
        extra_metrics = {
            "F1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
            "PR-AUC": round(float(average_precision_score(y_test, y_prob)), 4),
            "Accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        }
    elif problem_type == "multiclass":
        metric_name = "Macro F1"
        metric_value = round(float(f1_score(y_test, y_pred, average="macro", zero_division=0)), 4)
        extra_metrics = {
            "Accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        }
    else:
        metric_name = "R²"
        metric_value = round(float(r2_score(y_test, y_pred)), 4)
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        mae = float(mean_absolute_error(y_test, y_pred))
        # MAPE (avoid div by zero)
        nonzero = y_test != 0
        mape = float(np.mean(np.abs((y_test[nonzero] - y_pred[nonzero]) / y_test[nonzero]))) * 100 if nonzero.any() else None
        extra_metrics = {
            "RMSE": round(rmse, 4),
            "MAE": round(mae, 4),
        }
        if mape is not None:
            extra_metrics["MAPE%"] = round(mape, 2)

    # ── SHAP feature importance ────────────────────────────────────────────────
    feature_importance = {}
    try:
        explainer = shap.TreeExplainer(model)
        sample = X_test[:min(200, len(X_test))]
        shap_vals = explainer.shap_values(sample)

        if isinstance(shap_vals, list):
            # Multi-class: average absolute across classes
            shap_arr = np.mean([np.abs(sv) for sv in shap_vals], axis=0)
        else:
            shap_arr = np.abs(shap_vals)

        mean_shap = np.mean(shap_arr, axis=0)
        total = mean_shap.sum() or 1.0
        top_indices = np.argsort(mean_shap)[::-1][:10]
        feature_importance = {
            feature_cols[i]: round(float(mean_shap[i] / total), 4)
            for i in top_indices
        }
    except Exception:
        importances = model.feature_importances_
        total = importances.sum() or 1.0
        top_indices = np.argsort(importances)[::-1][:10]
        feature_importance = {
            feature_cols[i]: round(float(importances[i] / total), 4)
            for i in top_indices
        }

    return {
        "model_type": problem_type,
        "target_column": target_col,
        "feature_columns": feature_cols[:10],
        "is_time_series": is_ts,
        "lag_features_added": is_ts,
        "metric_name": metric_name,
        "metric_value": metric_value,
        "extra_metrics": extra_metrics,
        "feature_importance": feature_importance,
        "training_rows": len(X_train),
        "training_time_ms": int((time.time() - t0) * 1000),
        "trained_on": "Local",
        # internal
        "_model": model,
        "_X_test": X_test,
        "_y_test": y_test,
        "_feature_cols": feature_cols,
        "_is_classification": is_classification,
        "_problem_type": problem_type,
    }
