import pandas as pd
import numpy as np


def score_quality(df: pd.DataFrame, schema: dict) -> dict:
    columns_meta = schema.get("columns", {})

    # Completeness: 1 - mean(null_pct across all columns)
    null_pcts = [info.get("null_pct", 0.0) for info in columns_meta.values()]
    completeness = 1.0 - float(np.mean(null_pcts)) if null_pcts else 1.0

    # Outlier rate: fraction of rows where any numeric column > 3 std from mean
    numeric_cols = [
        col for col, info in columns_meta.items()
        if info.get("dtype") == "numeric" and col in df.columns
    ]

    if numeric_cols:
        outlier_mask = pd.Series([False] * len(df), index=df.index)
        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 2:
                continue
            mean = series.mean()
            std = series.std()
            if std == 0:
                continue
            col_outliers = ((df[col] - mean).abs() > 3 * std)
            outlier_mask = outlier_mask | col_outliers.fillna(False)
        outlier_rate = float(outlier_mask.mean())
    else:
        outlier_rate = 0.0

    # Drift score: coefficient of variation across 10 rolling windows for numeric cols
    if numeric_cols and len(df) >= 10:
        window_size = max(len(df) // 10, 5)
        cv_values = []
        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < window_size:
                continue
            window_means = []
            for i in range(10):
                start = i * (len(series) // 10)
                end = start + (len(series) // 10)
                segment = series.iloc[start:end]
                if len(segment) > 0 and segment.mean() != 0:
                    window_means.append(segment.mean())
            if len(window_means) >= 2:
                arr = np.array(window_means)
                mean_val = np.mean(arr)
                std_val = np.std(arr)
                cv = std_val / abs(mean_val) if mean_val != 0 else 0.0
                cv_values.append(cv)
        if cv_values:
            mean_cv = float(np.mean(cv_values))
            drift_score = float(np.clip(1.0 - mean_cv, 0.0, 1.0))
        else:
            drift_score = 1.0
    else:
        drift_score = 1.0

    overall_quality = (
        0.5 * completeness
        + 0.3 * (1.0 - outlier_rate)
        + 0.2 * drift_score
    )

    return {
        "completeness": round(completeness, 4),
        "outlier_rate": round(outlier_rate, 4),
        "drift_score": round(drift_score, 4),
        "overall_quality": round(float(np.clip(overall_quality, 0.0, 1.0)), 4),
    }
