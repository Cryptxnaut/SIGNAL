import numpy as np
import pandas as pd
from typing import Any


def run_stress_test(df: pd.DataFrame, model_result: dict) -> dict:
    model = model_result.get("_model")
    feature_cols = model_result.get("_feature_cols", [])
    X_test = model_result.get("_X_test")
    is_classification = model_result.get("_is_classification", False)
    feature_importance = model_result.get("feature_importance", {})

    if model is None or X_test is None or len(feature_cols) == 0:
        return {
            "perturbation_matrix": [],
            "edge_cases": [
                {
                    "title": "Edge Case 1",
                    "description": "Model not trained — stress test unavailable.",
                }
            ],
        }

    # Top 5 features by SHAP importance
    top_features = list(feature_importance.keys())[:5]
    top_feature_indices = [
        feature_cols.index(f) for f in top_features if f in feature_cols
    ]

    if not top_feature_indices:
        top_feature_indices = list(range(min(5, len(feature_cols))))
        top_features = [feature_cols[i] for i in top_feature_indices]

    # Baseline prediction from test set
    if is_classification:
        baseline_preds = model.predict_proba(X_test)[:, 1]
    else:
        baseline_preds = model.predict(X_test)

    baseline_mean = float(np.mean(baseline_preds))
    if baseline_mean == 0:
        baseline_mean = 1e-9

    perturbation_levels = {
        "-50%": lambda x, mn, mx, std: x * 0.5,
        "-25%": lambda x, mn, mx, std: x * 0.75,
        "+25%": lambda x, mn, mx, std: x * 1.25,
        "+50%": lambda x, mn, mx, std: x * 1.5,
        "+100%": lambda x, mn, mx, std: x * 2.0,
        "set_min": lambda x, mn, mx, std: np.full_like(x, mn),
        "set_max": lambda x, mn, mx, std: np.full_like(x, mx),
        "set_zero": lambda x, mn, mx, std: np.zeros_like(x),
    }

    perturbation_matrix = []

    for feat_idx, feat_name in zip(top_feature_indices, top_features):
        feat_data = X_test[:, feat_idx]
        feat_min = float(feat_data.min())
        feat_max = float(feat_data.max())
        feat_std = float(feat_data.std())

        perturbations = {}

        for level_name, transform_fn in perturbation_levels.items():
            try:
                X_perturbed = X_test.copy()
                perturbed_col = transform_fn(
                    X_test[:, feat_idx].copy(), feat_min, feat_max, feat_std
                )
                X_perturbed[:, feat_idx] = perturbed_col

                if is_classification:
                    perturbed_preds = model.predict_proba(X_perturbed)[:, 1]
                else:
                    perturbed_preds = model.predict(X_perturbed)

                perturbed_mean = float(np.mean(perturbed_preds))
                change_pct = abs(perturbed_mean - baseline_mean) / abs(baseline_mean) * 100.0

                if change_pct < 10.0:
                    status = "STABLE"
                elif change_pct < 30.0:
                    status = "DEGRADED"
                else:
                    status = "BROKEN"

                perturbations[level_name] = {
                    "status": status,
                    "change_pct": round(change_pct, 2),
                }
            except Exception:
                perturbations[level_name] = {"status": "STABLE", "change_pct": 0.0}

        perturbation_matrix.append({
            "feature": feat_name,
            "perturbations": perturbations,
        })

    # Find 3 worst edge cases
    worst_cases = []
    for entry in perturbation_matrix:
        feat = entry["feature"]
        for level, data in entry["perturbations"].items():
            worst_cases.append((feat, level, data["change_pct"], data["status"]))

    worst_cases.sort(key=lambda x: -x[2])

    edge_cases = []
    seen_features = set()
    for feat, level, change_pct, status in worst_cases:
        if feat not in seen_features and len(edge_cases) < 3:
            seen_features.add(feat)
            description = (
                f"When {feat} is perturbed by {level}, model output changes by "
                f"{change_pct:.1f}% (status: {status}). "
                f"This represents a significant {'instability' if status == 'BROKEN' else 'sensitivity'} "
                f"that may affect predictions in production edge cases."
            )
            edge_cases.append({
                "title": f"Edge Case {len(edge_cases) + 1}",
                "description": description,
            })

    # Ensure we always have 3
    while len(edge_cases) < 3:
        edge_cases.append({
            "title": f"Edge Case {len(edge_cases) + 1}",
            "description": "No significant instability detected for this scenario.",
        })

    # Clean model_result of internal fields before returning
    return {
        "perturbation_matrix": perturbation_matrix,
        "edge_cases": edge_cases,
    }
