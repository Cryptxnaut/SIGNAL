"""Statistical analysis pipeline — parallel execution with extended methods."""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from scipy import stats as scipy_stats
from sklearn.ensemble import IsolationForest
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.feature_selection import mutual_info_regression, mutual_info_classif
from sklearn.preprocessing import StandardScaler


# ─── helpers ───────────────────────────────────────────────────────────────────

def _numeric_cols(df: pd.DataFrame, schema: dict) -> list[str]:
    return [c for c, m in schema.get("columns", {}).items()
            if m.get("dtype") == "numeric" and c in df.columns]


def _safe_col(df: pd.DataFrame, col: str) -> pd.Series:
    return df[col].dropna()


def _cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return 0.0
    pooled_std = np.sqrt(((n1 - 1) * a.std() ** 2 + (n2 - 1) * b.std() ** 2) / (n1 + n2 - 2))
    return float(abs(a.mean() - b.mean()) / pooled_std) if pooled_std > 0 else 0.0


def _partial_corr(df: pd.DataFrame, x: str, y: str, controls: list[str]) -> tuple[float, float]:
    """Pearson partial correlation between x and y controlling for 'controls'."""
    try:
        cols = [x, y] + controls
        sub = df[cols].dropna()
        if len(sub) < 10:
            return 0.0, 1.0
        # Residualise x and y on controls
        from numpy.linalg import lstsq
        Z = np.column_stack([np.ones(len(sub))] + [sub[c].values for c in controls])
        rx = sub[x].values - Z @ lstsq(Z, sub[x].values, rcond=None)[0]
        ry = sub[y].values - Z @ lstsq(Z, sub[y].values, rcond=None)[0]
        r, p = scipy_stats.pearsonr(rx, ry)
        return float(r), float(p)
    except Exception:
        return 0.0, 1.0


# ─── individual analysis functions ─────────────────────────────────────────────

def _run_correlation(df: pd.DataFrame, h: dict, schema: dict) -> dict:
    target = h.get("target_column")
    features = h.get("feature_columns", [])
    num_cols = _numeric_cols(df, schema)

    if not target or target not in df.columns:
        target = num_cols[0] if num_cols else None
    if not target:
        return {}
    features = [c for c in (features or num_cols) if c != target and c in df.columns]
    if not features:
        features = [c for c in num_cols if c != target][:5]
    if not features:
        return {}

    sub = df[[target] + features].dropna()
    if len(sub) < 10:
        return {}

    correlations = []
    controls = [c for c in features if c != features[0]][:3]  # partial corr controls

    for feat in features:
        try:
            pr, pp = scipy_stats.pearsonr(sub[target], sub[feat])
            sr, sp = scipy_stats.spearmanr(sub[target], sub[feat])
            pcr, pcp = _partial_corr(df, target, feat, controls[:2]) if len(controls) >= 1 else (pr, pp)
            # Effect size (Cohen's d on median split)
            med = sub[feat].median()
            d = _cohens_d(sub[sub[feat] >= med][target].values, sub[sub[feat] < med][target].values)
            correlations.append({
                "column": feat,
                "pearson_r": round(float(pr), 4),
                "pearson_p": round(float(pp), 6),
                "spearman_r": round(float(sr), 4),
                "spearman_p": round(float(sp), 6),
                "partial_r": round(float(pcr), 4),
                "partial_p": round(float(pcp), 6),
                "cohens_d": round(d, 4),
                "direction": "positive" if pr > 0 else "negative",
            })
        except Exception:
            continue

    if not correlations:
        return {}

    correlations.sort(key=lambda x: x["pearson_p"])
    top = correlations[0]
    sig = 1 - top["pearson_p"]

    return {
        "type": "correlation",
        "name": h.get("name", f"Correlation: {target}"),
        "description": h.get("description", ""),
        "target_column": target,
        "feature_columns": features,
        "correlations": correlations[:10],
        "top_correlation": {"column": top["column"], "r": top["pearson_r"], "p": top["pearson_p"], "cohens_d": top["cohens_d"]},
        "significance_score": round(sig, 6),
    }


def _run_mutual_info(df: pd.DataFrame, h: dict, schema: dict) -> dict:
    """Detect non-linear relationships using mutual information."""
    target = h.get("target_column")
    num_cols = _numeric_cols(df, schema)
    if not target or target not in df.columns:
        target = num_cols[0] if num_cols else None
    if not target:
        return {}

    features = [c for c in num_cols if c != target][:10]
    if not features:
        return {}

    sub = df[[target] + features].dropna()
    if len(sub) < 20:
        return {}

    X = sub[features].values
    y = sub[target].values

    # Detect if classification target
    unique_vals = np.unique(y)
    is_clf = len(unique_vals) <= 10 and set(unique_vals).issubset(set(range(20)))

    try:
        if is_clf:
            mi = mutual_info_classif(X, y.astype(int), random_state=42)
        else:
            mi = mutual_info_regression(X, y, random_state=42)
    except Exception:
        return {}

    mi_results = sorted(
        [{"column": feat, "mutual_info": round(float(mi[i]), 4)} for i, feat in enumerate(features)],
        key=lambda x: -x["mutual_info"]
    )

    top = mi_results[0] if mi_results else None
    if not top:
        return {}

    # Compare with Pearson to find non-linear signals (high MI, low Pearson = non-linear)
    for item in mi_results:
        try:
            pr, _ = scipy_stats.pearsonr(sub[item["column"]], sub[target])
            item["pearson_r"] = round(float(pr), 4)
            item["nonlinearity"] = round(float(item["mutual_info"] - abs(pr)), 4)
        except Exception:
            item["pearson_r"] = 0.0
            item["nonlinearity"] = 0.0

    sig = float(top["mutual_info"]) / (float(top["mutual_info"]) + 1.0)

    return {
        "type": "mutual_info",
        "name": h.get("name", f"Non-linear signals in {target}"),
        "description": h.get("description", ""),
        "target_column": target,
        "feature_columns": features,
        "mi_results": mi_results[:8],
        "top_predictor": top,
        "significance_score": round(sig, 6),
    }


def _run_anomaly(df: pd.DataFrame, h: dict, schema: dict) -> dict:
    num_cols = _numeric_cols(df, schema)
    features = [c for c in h.get("feature_columns", num_cols) if c in df.columns]
    if not features:
        features = num_cols[:5]
    if not features:
        return {}

    sub = df[features].dropna()
    if len(sub) < 10:
        return {}

    try:
        clf = IsolationForest(contamination=0.1, random_state=42, n_jobs=-1)
        scores = clf.fit_predict(sub)
        iso_scores = clf.score_samples(sub)
        anomaly_mask = scores == -1
        anomaly_rate = float(anomaly_mask.mean())

        # Per-column Z-score anomalies for additional context
        z_anomalies = {}
        for col in features:
            z = np.abs(scipy_stats.zscore(sub[col].values))
            z_anomalies[col] = int((z > 3).sum())

        top_anomalous = (
            pd.Series(iso_scores, index=sub.index)
            .nsmallest(10)
            .reset_index()
        )
        top_rows = [
            {"index": int(r.iloc[0]), "score": round(float(r.iloc[1]), 4)}
            for _, r in top_anomalous.iterrows()
        ]

        return {
            "type": "anomaly",
            "name": h.get("name", "Anomaly detection"),
            "description": h.get("description", ""),
            "feature_columns": features,
            "anomaly_rate": round(anomaly_rate, 4),
            "anomalous_rows": top_rows,
            "z_score_anomalies": z_anomalies,
            "significance_score": round(anomaly_rate, 4),
        }
    except Exception:
        return {}


def _run_trend(df: pd.DataFrame, h: dict, schema: dict) -> dict:
    target = h.get("target_column")
    num_cols = _numeric_cols(df, schema)
    if not target or target not in df.columns:
        target = num_cols[0] if num_cols else None
    if not target:
        return {}

    series = _safe_col(df, target)
    if len(series) < 8:
        return {}

    try:
        # STL decomposition
        if len(series) >= 24:
            from statsmodels.tsa.seasonal import STL
            stl = STL(series.reset_index(drop=True), period=min(12, len(series) // 3), robust=True)
            result = stl.fit()
            trend_vals = result.trend
            seasonal_vals = result.seasonal
            resid_vals = result.resid
            season_str = float(np.var(seasonal_vals) / (np.var(series.values) + 1e-9))
            resid_var = float(np.var(resid_vals))
        else:
            trend_vals = series.rolling(3, min_periods=1).mean().values
            season_str = 0.0
            resid_var = float(np.var(series.values - trend_vals))

        # Trend direction via Mann-Kendall-like test
        n = len(trend_vals)
        slope, intercept, r, p, _ = scipy_stats.linregress(np.arange(n), trend_vals)
        if p < 0.05:
            direction = "increasing" if slope > 0 else "decreasing"
        else:
            direction = "stable"

        # Trend magnitude (% change)
        trend_change_pct = 0.0
        if abs(trend_vals[0]) > 1e-6:
            trend_change_pct = round(float((trend_vals[-1] - trend_vals[0]) / abs(trend_vals[0]) * 100), 2)

        sig = 1 - float(p)

        return {
            "type": "trend",
            "name": h.get("name", f"Trend: {target}"),
            "description": h.get("description", ""),
            "target_column": target,
            "trend_direction": direction,
            "trend_slope": round(float(slope), 6),
            "trend_change_pct": trend_change_pct,
            "seasonality_strength": round(season_str, 4),
            "residual_variance": round(resid_var, 4),
            "trend_p_value": round(float(p), 6),
            "significance_score": round(sig, 6),
        }
    except Exception:
        return {}


def _run_leading_indicator(df: pd.DataFrame, h: dict, schema: dict) -> dict:
    target = h.get("target_column")
    features = h.get("feature_columns", [])
    num_cols = _numeric_cols(df, schema)
    if not target or target not in df.columns:
        target = num_cols[0] if num_cols else None
    if not target:
        return {}
    features = [c for c in (features or num_cols) if c != target and c in df.columns][:4]
    if not features:
        return {}

    sub = df[[target] + features].dropna().reset_index(drop=True)
    if len(sub) < 20:
        return {}

    granger_results = []
    max_lags = min(12, len(sub) // 5)

    try:
        from statsmodels.tsa.stattools import grangercausalitytests
        for feat in features:
            try:
                pair = sub[[target, feat]].dropna()
                if len(pair) < max_lags + 5:
                    continue
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    res = grangercausalitytests(pair, maxlag=max_lags, verbose=False)
                best_lag, best_p = min(
                    ((lag, min(v[0][test][1] for test in ["ssr_chi2test", "ssr_ftest"]))
                     for lag, v in res.items()),
                    key=lambda x: x[1]
                )
                granger_results.append({
                    "column": feat,
                    "best_lag": best_lag,
                    "p_value": round(float(best_p), 6),
                })
            except Exception:
                continue

        if not granger_results:
            return {}

        granger_results.sort(key=lambda x: x["p_value"])
        top = granger_results[0]
        sig = 1 - top["p_value"]

        return {
            "type": "leading_indicator",
            "name": h.get("name", f"Leading indicators of {target}"),
            "description": h.get("description", ""),
            "target_column": target,
            "feature_columns": features,
            "granger_results": granger_results,
            "top_indicator": top,
            "significance_score": round(sig, 6),
        }
    except Exception:
        return {}


def _run_regime_change(df: pd.DataFrame, h: dict, schema: dict) -> dict:
    target = h.get("target_column")
    num_cols = _numeric_cols(df, schema)
    if not target or target not in df.columns:
        target = num_cols[0] if num_cols else None
    if not target:
        return {}

    series = _safe_col(df, target).reset_index(drop=True)
    if len(series) < 10:
        return {}

    try:
        vals = series.values.astype(float)
        mu = np.mean(vals)
        sigma = np.std(vals)
        if sigma < 1e-9:
            return {}

        # CUSUM
        cusum_pos = np.zeros(len(vals))
        cusum_neg = np.zeros(len(vals))
        k = 0.5 * sigma
        threshold = 3.0 * sigma

        for i in range(1, len(vals)):
            cusum_pos[i] = max(0, cusum_pos[i - 1] + vals[i] - mu - k)
            cusum_neg[i] = min(0, cusum_neg[i - 1] + vals[i] - mu + k)

        cp_pos = np.where(cusum_pos > threshold)[0]
        cp_neg = np.where(cusum_neg < -threshold)[0]

        changepoints = []
        for idx in cp_pos[:10]:
            changepoints.append({"index": int(idx), "direction": "upward", "magnitude": round(float(cusum_pos[idx] / sigma), 3)})
        for idx in cp_neg[:10]:
            changepoints.append({"index": int(idx), "direction": "downward", "magnitude": round(float(abs(cusum_neg[idx]) / sigma), 3)})
        changepoints.sort(key=lambda x: -x["magnitude"])

        sig = min(1.0, len(changepoints) / 5.0) if changepoints else 0.0

        return {
            "type": "regime_change",
            "name": h.get("name", f"Regime changes in {target}"),
            "description": h.get("description", ""),
            "target_column": target,
            "changepoints": changepoints[:20],
            "n_changepoints": len(changepoints),
            "significance_score": round(sig, 4),
        }
    except Exception:
        return {}


def _run_clustering(df: pd.DataFrame, h: dict, schema: dict) -> dict:
    """K-means clustering to find natural groupings."""
    num_cols = _numeric_cols(df, schema)
    features = [c for c in h.get("feature_columns", num_cols) if c in df.columns][:8]
    if len(features) < 2:
        return {}

    sub = df[features].dropna()
    if len(sub) < 20:
        return {}

    try:
        scaler = StandardScaler()
        X = scaler.fit_transform(sub.values)

        best_k, best_score, best_labels = 2, -1.0, None
        for k in range(2, min(7, len(sub) // 5 + 1)):
            km = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = km.fit_predict(X)
            if len(set(labels)) < 2:
                continue
            score = float(silhouette_score(X, labels))
            if score > best_score:
                best_k = k
                best_score = score
                best_labels = labels

        if best_labels is None:
            return {}

        # Cluster profiles
        sub_copy = sub.copy()
        sub_copy["_cluster"] = best_labels
        profiles = []
        for k in range(best_k):
            mask = best_labels == k
            profile = {"cluster": k, "size": int(mask.sum()), "pct": round(float(mask.mean()) * 100, 1)}
            for feat in features[:4]:
                profile[f"mean_{feat}"] = round(float(sub[feat].values[mask].mean()), 4)
            profiles.append(profile)

        sig = round((best_score + 1) / 2, 4)  # normalise -1..1 to 0..1

        return {
            "type": "clustering",
            "name": h.get("name", f"Natural groupings ({best_k} clusters)"),
            "description": h.get("description", ""),
            "feature_columns": features,
            "n_clusters": best_k,
            "silhouette_score": round(best_score, 4),
            "cluster_profiles": profiles,
            "significance_score": sig,
        }
    except Exception:
        return {}


# ─── dispatch table ─────────────────────────────────────────────────────────────

_RUNNERS = {
    "correlation": _run_correlation,
    "mutual_info": _run_mutual_info,
    "anomaly": _run_anomaly,
    "trend": _run_trend,
    "leading_indicator": _run_leading_indicator,
    "regime_change": _run_regime_change,
    "clustering": _run_clustering,
}


def run_stats(df: pd.DataFrame, hypotheses: list, schema: dict) -> list:
    """Run all hypothesis tests in parallel using a thread pool."""
    if not hypotheses:
        return []

    results = []

    def _run_one(h: dict) -> dict | None:
        htype = h.get("type", "correlation")
        runner = _RUNNERS.get(htype, _run_correlation)
        try:
            result = runner(df, h, schema)
            return result if result else None
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=min(8, len(hypotheses))) as executor:
        futures = {executor.submit(_run_one, h): h for h in hypotheses}
        for future in as_completed(futures):
            try:
                result = future.result(timeout=30)
                if result:
                    results.append(result)
            except Exception:
                continue

    return results
