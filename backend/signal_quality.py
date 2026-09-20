"""
Signal quality framework — separates genuine signals from spurious correlations.

Three pillars:
  1. Walk-forward validation  — does the signal hold out-of-sample?
  2. Bootstrap stability      — is the signal statistically robust?
  3. Signal persistence       — does the signal decay, or strengthen over time?

Combined into a single Signal Quality Score (SQS) per finding.
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from sklearn.utils import resample as sk_resample


# ═══════════════════════════════════════════════════════════════════════════════
# WALK-FORWARD VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def walk_forward_correlation(
    x: np.ndarray,
    y: np.ndarray,
    n_splits: int = 5,
    min_train: int = 20,
) -> dict:
    """
    Walk-forward test of Pearson correlation.
    Train on expanding window, test on next slice.
    Returns: mean OOS correlation, std, and fraction of positive OOS windows.
    """
    n = min(len(x), len(y))
    x, y = x[:n], y[:n]

    if n < min_train * 2:
        return {"oos_mean_r": None, "oos_std_r": None, "positive_fraction": None}

    step = max(1, (n - min_train) // n_splits)
    oos_correlations = []

    for split in range(n_splits):
        train_end = min_train + split * step
        test_end = min(train_end + step, n)
        if test_end <= train_end:
            break
        # In-sample: up to train_end
        # Out-of-sample: train_end:test_end
        x_oos = x[train_end:test_end]
        y_oos = y[train_end:test_end]
        if len(x_oos) < 5:
            continue
        try:
            r, _ = scipy_stats.pearsonr(x_oos, y_oos)
            oos_correlations.append(float(r))
        except Exception:
            continue

    if not oos_correlations:
        return {"oos_mean_r": None, "oos_std_r": None, "positive_fraction": None}

    oos_arr = np.array(oos_correlations)
    in_sample_r, _ = scipy_stats.pearsonr(x, y)

    return {
        "in_sample_r": round(float(in_sample_r), 4),
        "oos_mean_r": round(float(oos_arr.mean()), 4),
        "oos_std_r": round(float(oos_arr.std()), 4),
        "positive_fraction": round(float((oos_arr > 0).mean()), 4),
        "degradation": round(float(abs(in_sample_r) - abs(oos_arr.mean())), 4),
        "n_windows": len(oos_correlations),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# BOOTSTRAP CONFIDENCE INTERVALS
# ═══════════════════════════════════════════════════════════════════════════════

def bootstrap_correlation(
    x: np.ndarray,
    y: np.ndarray,
    n_bootstrap: int = 500,
    ci: float = 0.95,
) -> dict:
    """
    Bootstrap confidence interval for Pearson correlation.
    A narrow CI crossing zero indicates an unreliable signal.
    A CI that excludes zero is a robust finding.
    """
    x = x[~np.isnan(x)]
    y = y[~np.isnan(y)]
    n = min(len(x), len(y))
    x, y = x[:n], y[:n]

    if n < 10:
        return {}

    boot_r = []
    idx = np.arange(n)
    for _ in range(n_bootstrap):
        sample_idx = np.random.choice(idx, size=n, replace=True)
        xs, ys = x[sample_idx], y[sample_idx]
        try:
            r, _ = scipy_stats.pearsonr(xs, ys)
            boot_r.append(r)
        except Exception:
            continue

    if not boot_r:
        return {}

    boot_arr = np.array(boot_r)
    alpha = 1 - ci
    lo = float(np.percentile(boot_arr, 100 * alpha / 2))
    hi = float(np.percentile(boot_arr, 100 * (1 - alpha / 2)))
    point_r, _ = scipy_stats.pearsonr(x, y)

    return {
        "point_r": round(float(point_r), 4),
        "ci_lower": round(lo, 4),
        "ci_upper": round(hi, 4),
        "ci_excludes_zero": (lo > 0) or (hi < 0),
        "ci_width": round(hi - lo, 4),
        "n_bootstrap": len(boot_r),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ROLLING CORRELATION STABILITY
# ═══════════════════════════════════════════════════════════════════════════════

def rolling_correlation_stability(
    x: np.ndarray,
    y: np.ndarray,
    n_windows: int = 10,
) -> dict:
    """
    Measure how stable a correlation is across rolling windows.
    High mean + low std = persistent, reliable signal.
    High mean + high std = spurious or regime-dependent.
    """
    n = min(len(x), len(y))
    if n < 30:
        return {}

    x, y = x[:n], y[:n]
    window = n // n_windows
    if window < 5:
        return {}

    window_rs = []
    for i in range(n_windows):
        s = i * window
        e = s + window
        if e > n:
            break
        try:
            r, _ = scipy_stats.pearsonr(x[s:e], y[s:e])
            window_rs.append(float(r))
        except Exception:
            continue

    if len(window_rs) < 3:
        return {}

    arr = np.array(window_rs)
    return {
        "window_correlations": [round(v, 4) for v in arr],
        "mean_r": round(float(arr.mean()), 4),
        "std_r": round(float(arr.std()), 4),
        "consistency": round(float(1 - arr.std() / (abs(arr.mean()) + 1e-6)), 4),
        "sign_flips": int(np.sum(np.diff(np.sign(arr)) != 0)),
        "trend": "strengthening" if arr[-1] > arr[0] else "weakening" if arr[-1] < arr[0] else "stable",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNAL QUALITY SCORE
# ═══════════════════════════════════════════════════════════════════════════════

def compute_signal_quality_score(
    df: pd.DataFrame,
    finding: dict,
) -> dict:
    """
    Composite Signal Quality Score (SQS) for a correlation finding.

    SQS = 0.35 * oos_score + 0.35 * bootstrap_score + 0.30 * stability_score

    Where:
      oos_score       = OOS correlation magnitude * sign consistency
      bootstrap_score = 1 if CI excludes zero, else 0.5 * (1 - CI width)
      stability_score = rolling consistency score

    SQS range: 0 (pure noise) to 1 (extremely reliable signal)
    """
    ftype = finding.get("type")
    if ftype != "correlation":
        return {}

    target = finding.get("target_column")
    top_corr = finding.get("top_correlation", {})
    feature = top_corr.get("column")

    if not target or not feature:
        return {}
    if target not in df.columns or feature not in df.columns:
        return {}

    sub = df[[target, feature]].dropna()
    if len(sub) < 20:
        return {}

    x = sub[feature].values
    y = sub[target].values

    wf = walk_forward_correlation(x, y)
    bs = bootstrap_correlation(x, y)
    rs = rolling_correlation_stability(x, y)

    # OOS score
    oos_r = wf.get("oos_mean_r")
    pos_frac = wf.get("positive_fraction", 0.5) or 0.5
    oos_score = abs(oos_r) * pos_frac if oos_r is not None else 0.3

    # Bootstrap score
    ci_excl = bs.get("ci_excludes_zero", False)
    ci_width = bs.get("ci_width", 1.0) or 1.0
    bootstrap_score = 0.9 if ci_excl else max(0.0, 0.5 - ci_width / 2)

    # Stability score
    consistency = rs.get("consistency", 0.5) or 0.5
    sign_flips = rs.get("sign_flips", 5)
    stability_score = max(0.0, consistency * (1 - sign_flips * 0.1))

    sqs = 0.35 * oos_score + 0.35 * bootstrap_score + 0.30 * stability_score

    grade = "A" if sqs > 0.7 else "B" if sqs > 0.5 else "C" if sqs > 0.35 else "D"

    return {
        "signal_quality_score": round(float(sqs), 4),
        "grade": grade,
        "walk_forward": wf,
        "bootstrap_ci": bs,
        "rolling_stability": rs,
        "interpretation": _interpret_sqs(sqs, wf, bs, rs),
    }


def _interpret_sqs(sqs, wf, bs, rs) -> str:
    parts = []
    if wf.get("oos_mean_r") is not None:
        deg = wf.get("degradation", 0)
        if deg > 0.2:
            parts.append(f"significant in-sample overfitting (OOS degradation: {deg:.2f})")
        elif deg < 0.05:
            parts.append("strong out-of-sample persistence")
    if bs.get("ci_excludes_zero"):
        parts.append(f"bootstrap CI [{bs['ci_lower']:.3f}, {bs['ci_upper']:.3f}] excludes zero")
    sign_flips = rs.get("sign_flips", 0)
    if sign_flips > 3:
        parts.append(f"unstable across windows ({sign_flips} sign reversals)")
    elif rs.get("consistency", 0) > 0.7:
        parts.append("consistent across all time windows")
    if not parts:
        return "Moderate signal quality — further validation recommended."
    return " · ".join(parts).capitalize() + "."


# ═══════════════════════════════════════════════════════════════════════════════
# BATCH SQS ENRICHMENT
# ═══════════════════════════════════════════════════════════════════════════════

def enrich_findings_with_sqs(df: pd.DataFrame, findings: list) -> list:
    """
    Attach signal quality scores to all correlation-type findings.
    Modifies findings in-place (adds 'signal_quality' key).
    """
    enriched = []
    for finding in findings:
        f = dict(finding)
        if f.get("type") == "correlation":
            try:
                sqs = compute_signal_quality_score(df, f)
                if sqs:
                    f["signal_quality"] = sqs
                    # Update composite score with SQS bonus
                    sqs_val = sqs.get("signal_quality_score", 0)
                    f["composite_score"] = round(
                        f.get("composite_score", 0.5) * 0.7 + sqs_val * 0.3, 4
                    )
            except Exception:
                pass
        enriched.append(f)
    return enriched
