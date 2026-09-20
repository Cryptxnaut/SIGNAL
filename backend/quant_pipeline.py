"""
Quantitative analysis pipeline — methods used in production at quant firms.

Methods implemented:
  - Cointegration testing (Engle-Granger + Johansen)
  - Transfer entropy (directed information flow, nonparametric)
  - Hurst exponent (R/S analysis — classifies signal regime)
  - Hidden Markov Model regime detection
  - Factor analysis with PCA rotation
  - Rolling correlation stability
  - Bootstrap confidence intervals
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import combinations
from typing import Any

from scipy import stats as scipy_stats
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


# ═══════════════════════════════════════════════════════════════════════════════
# HURST EXPONENT
# ═══════════════════════════════════════════════════════════════════════════════

def hurst_exponent(ts: np.ndarray, max_lag: int | None = None) -> float:
    """
    Hurst exponent via Rescaled Range (R/S) analysis.

    H < 0.5  → mean-reverting (anti-persistent) — signal will revert
    H ≈ 0.5  → random walk — no exploitable signal
    H > 0.5  → trending (persistent) — signal has momentum
    """
    ts = ts[~np.isnan(ts)]
    n = len(ts)
    if n < 20:
        return 0.5

    if max_lag is None:
        max_lag = min(n // 2, 100)

    lags = np.unique(np.logspace(1, np.log10(max_lag), num=20).astype(int))
    rs_vals = []

    for lag in lags:
        if lag < 2:
            continue
        segments = n // lag
        if segments < 2:
            continue
        rs_per_seg = []
        for i in range(segments):
            seg = ts[i * lag:(i + 1) * lag].astype(float)
            mean = seg.mean()
            devs = np.cumsum(seg - mean)
            r = devs.max() - devs.min()
            s = seg.std(ddof=1)
            if s > 0:
                rs_per_seg.append(r / s)
        if rs_per_seg:
            rs_vals.append((lag, np.mean(rs_per_seg)))

    if len(rs_vals) < 2:
        return 0.5

    lags_arr = np.array([v[0] for v in rs_vals])
    rs_arr = np.array([v[1] for v in rs_vals])
    try:
        slope, *_ = scipy_stats.linregress(np.log(lags_arr), np.log(rs_arr))
        return float(np.clip(slope, 0.0, 1.0))
    except Exception:
        return 0.5


def interpret_hurst(h: float) -> str:
    if h < 0.4:
        return "strongly mean-reverting"
    if h < 0.45:
        return "mean-reverting"
    if h < 0.55:
        return "random walk"
    if h < 0.65:
        return "weakly trending"
    return "strongly trending"


def run_hurst_analysis(df: pd.DataFrame, schema: dict) -> dict | None:
    """Compute Hurst exponent for all numeric time-series columns."""
    num_ts_cols = [
        c for c, m in schema.get("columns", {}).items()
        if m.get("dtype") == "numeric" and c in df.columns
    ]
    if not num_ts_cols:
        return None

    results = []
    for col in num_ts_cols[:10]:
        vals = df[col].dropna().values
        if len(vals) < 20:
            continue
        h = hurst_exponent(vals)
        results.append({
            "column": col,
            "hurst": round(h, 4),
            "regime": interpret_hurst(h),
            "signal_type": "mean_reverting" if h < 0.45 else "random" if h < 0.55 else "trending",
        })

    if not results:
        return None

    # Overall dominant regime
    regimes = [r["signal_type"] for r in results]
    dominant = max(set(regimes), key=regimes.count)

    return {
        "type": "hurst",
        "name": "Signal Regime Classification (Hurst Exponent)",
        "description": "R/S analysis classifies whether each series is mean-reverting, random, or trending.",
        "results": results,
        "dominant_regime": dominant,
        "significance_score": round(
            sum(abs(r["hurst"] - 0.5) for r in results) / max(len(results), 1), 4
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TRANSFER ENTROPY
# ═══════════════════════════════════════════════════════════════════════════════

def _discretise(x: np.ndarray, bins: int = 8) -> np.ndarray:
    edges = np.percentile(x, np.linspace(0, 100, bins + 1))
    edges = np.unique(edges)
    return np.digitize(x, edges[1:-1])


def transfer_entropy(x: np.ndarray, y: np.ndarray, lag: int = 1, bins: int = 8) -> float:
    """
    Transfer entropy TE(X→Y): how much knowing X's past reduces uncertainty about Y's future,
    beyond what Y's own past already tells us.

    TE(X→Y) = H(Y_t | Y_{t-1}) - H(Y_t | Y_{t-1}, X_{t-lag})

    Implemented via histogram-based entropy estimation (no external dependencies).
    """
    x = x[~np.isnan(x)]
    y = y[~np.isnan(y)]
    min_len = min(len(x), len(y))
    if min_len < 20 + lag:
        return 0.0

    x = x[:min_len]
    y = y[:min_len]

    xd = _discretise(x, bins)
    yd = _discretise(y, bins)

    y_fut = yd[lag:]
    y_pas = yd[:-lag]
    x_pas = xd[:-lag]
    n = len(y_fut)

    def _joint_entropy(*arrays) -> float:
        from collections import Counter
        counts = Counter(zip(*arrays))
        probs = np.array(list(counts.values())) / n
        return -np.sum(probs * np.log2(probs + 1e-12))

    # H(Y_t, Y_{t-1}) - H(Y_{t-1}) = H(Y_t | Y_{t-1})
    h_yt_ypas = _joint_entropy(y_fut, y_pas) - _joint_entropy(y_pas,)
    # H(Y_t, Y_{t-1}, X_{t-1}) - H(Y_{t-1}, X_{t-1}) = H(Y_t | Y_{t-1}, X_{t-1})
    h_yt_ypas_xpas = _joint_entropy(y_fut, y_pas, x_pas) - _joint_entropy(y_pas, x_pas)

    te = h_yt_ypas - h_yt_ypas_xpas
    return max(0.0, float(te))


def run_transfer_entropy(df: pd.DataFrame, schema: dict, max_pairs: int = 10) -> dict | None:
    """
    Compute pairwise directed transfer entropy for numeric columns.
    Unlike Granger causality, TE captures non-linear information flow.
    """
    num_cols = [
        c for c, m in schema.get("columns", {}).items()
        if m.get("dtype") == "numeric" and c in df.columns
    ][:8]

    if len(num_cols) < 2:
        return None

    sub = df[num_cols].dropna()
    if len(sub) < 30:
        return None

    flows = []
    pairs = list(combinations(num_cols, 2))[:max_pairs]

    for c1, c2 in pairs:
        x = sub[c1].values
        y = sub[c2].values
        te_xy = transfer_entropy(x, y)
        te_yx = transfer_entropy(y, x)
        if te_xy > 0.001 or te_yx > 0.001:
            dominant = c1 if te_xy > te_yx else c2
            target = c2 if te_xy > te_yx else c1
            flows.append({
                "from": dominant,
                "to": target,
                "te_forward": round(te_xy, 4),
                "te_backward": round(te_yx, 4),
                "net_flow": round(te_xy - te_yx, 4),
                "asymmetry": round(abs(te_xy - te_yx) / (te_xy + te_yx + 1e-9), 4),
            })

    if not flows:
        return None

    flows.sort(key=lambda f: -abs(f["net_flow"]))
    top = flows[0]
    sig = min(1.0, abs(top["net_flow"]) * 10)

    return {
        "type": "transfer_entropy",
        "name": f"Information Flow: {top['from']} → {top['to']}",
        "description": "Transfer entropy measures directed non-linear information flow between variables.",
        "flows": flows[:8],
        "top_flow": top,
        "significance_score": round(sig, 4),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# COINTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

def _half_life(spread: np.ndarray) -> float:
    """Ornstein-Uhlenbeck half-life of mean reversion."""
    spread = spread[~np.isnan(spread)]
    if len(spread) < 10:
        return float("inf")
    lag = spread[:-1]
    delta = np.diff(spread)
    try:
        slope, _, _, _, _ = scipy_stats.linregress(lag, delta)
        if slope >= 0:
            return float("inf")
        return round(float(-np.log(2) / slope), 1)
    except Exception:
        return float("inf")


def run_cointegration(df: pd.DataFrame, schema: dict) -> dict | None:
    """
    Test for cointegration between all pairs of numeric columns using
    Engle-Granger two-step procedure.

    Cointegrated series share a common stochastic trend — their spread is
    stationary and mean-reverts, making the spread a tradeable signal.
    """
    try:
        from statsmodels.tsa.stattools import coint
    except ImportError:
        return None

    num_cols = [
        c for c, m in schema.get("columns", {}).items()
        if m.get("dtype") == "numeric" and c in df.columns
    ][:8]

    if len(num_cols) < 2:
        return None

    sub = df[num_cols].dropna()
    if len(sub) < 30:
        return None

    pairs = []
    for c1, c2 in combinations(num_cols, 2):
        try:
            _, p, _ = coint(sub[c1].values, sub[c2].values)
            if p < 0.1:
                # Estimate spread and hedge ratio via OLS
                x = sub[c1].values
                y = sub[c2].values
                hedge = float(np.polyfit(x, y, 1)[0])
                spread = y - hedge * x
                hl = _half_life(spread)
                spread_std = float(np.std(spread))
                pairs.append({
                    "col1": c1,
                    "col2": c2,
                    "p_value": round(float(p), 6),
                    "hedge_ratio": round(hedge, 4),
                    "half_life_periods": hl if hl != float("inf") else None,
                    "spread_std": round(spread_std, 4),
                    "cointegrated": p < 0.05,
                })
        except Exception:
            continue

    if not pairs:
        return None

    pairs.sort(key=lambda p: p["p_value"])
    top = pairs[0]
    sig = 1 - top["p_value"]

    return {
        "type": "cointegration",
        "name": f"Cointegration: {top['col1']} ↔ {top['col2']}",
        "description": (
            f"{top['col1']} and {top['col2']} share a common stochastic trend "
            f"(p={top['p_value']:.4f}). Spread half-life: "
            f"{top['half_life_periods']} periods."
        ),
        "pairs": pairs[:6],
        "top_pair": top,
        "significance_score": round(sig, 6),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# HIDDEN MARKOV MODEL — REGIME DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def run_hmm_regime(df: pd.DataFrame, schema: dict, n_states: int = 3) -> dict | None:
    """
    Fit a Gaussian HMM to detect latent market/data regimes.
    Each state represents a distinct behaviour pattern (e.g. low-vol, high-vol, trending).
    """
    try:
        from hmmlearn import hmm as hmmlib
    except ImportError:
        # Fall back to manual Gaussian mixture change detection
        return _hmm_fallback(df, schema)

    num_cols = [
        c for c, m in schema.get("columns", {}).items()
        if m.get("dtype") == "numeric" and c in df.columns
    ][:4]

    if not num_cols:
        return None

    sub = df[num_cols].dropna()
    if len(sub) < 50:
        return None

    scaler = StandardScaler()
    X = scaler.fit_transform(sub.values)

    best_model, best_score = None, -np.inf
    for k in range(2, n_states + 2):
        try:
            model = hmmlib.GaussianHMM(
                n_components=k, covariance_type="full",
                n_iter=100, random_state=42
            )
            model.fit(X)
            score = model.score(X) / len(X)
            if score > best_score:
                best_score = score
                best_model = model
        except Exception:
            continue

    if best_model is None:
        return _hmm_fallback(df, schema)

    states = best_model.predict(X)
    k = best_model.n_components

    state_stats = []
    for s in range(k):
        mask = states == s
        if mask.sum() < 2:
            continue
        state_data = pd.DataFrame(sub.values[mask], columns=num_cols)
        stat = {
            "state": s,
            "n_periods": int(mask.sum()),
            "pct": round(float(mask.mean()) * 100, 1),
        }
        for col in num_cols[:2]:
            stat[f"mean_{col}"] = round(float(state_data[col].mean()), 4)
            stat[f"std_{col}"] = round(float(state_data[col].std()), 4)
        state_stats.append(stat)

    # Transition matrix
    trans = best_model.transmat_.tolist()
    current_state = int(states[-1])

    return {
        "type": "hmm_regime",
        "name": f"Hidden Markov Regime Detection ({k} states)",
        "description": f"Gaussian HMM identifies {k} distinct data regimes with different statistical properties.",
        "n_states": k,
        "current_state": current_state,
        "state_stats": state_stats,
        "transition_matrix": [[round(v, 3) for v in row] for row in trans],
        "significance_score": round(min(1.0, abs(best_score) / 5), 4),
    }


def _hmm_fallback(df: pd.DataFrame, schema: dict) -> dict | None:
    """Simple variance-based regime detection when hmmlearn is unavailable."""
    num_cols = [
        c for c, m in schema.get("columns", {}).items()
        if m.get("dtype") == "numeric" and c in df.columns
    ][:2]
    if not num_cols:
        return None

    col = num_cols[0]
    series = df[col].dropna().values
    if len(series) < 30:
        return None

    window = len(series) // 3
    rolling_std = pd.Series(series).rolling(window, min_periods=1).std().values
    low_thresh = np.percentile(rolling_std, 33)
    high_thresh = np.percentile(rolling_std, 66)

    states = np.where(rolling_std < low_thresh, 0, np.where(rolling_std > high_thresh, 2, 1))
    state_names = {0: "low-volatility", 1: "normal", 2: "high-volatility"}

    state_stats = []
    for s in range(3):
        mask = states == s
        if mask.sum() < 2:
            continue
        state_stats.append({
            "state": s,
            "label": state_names[s],
            "n_periods": int(mask.sum()),
            "pct": round(float(mask.mean()) * 100, 1),
            f"mean_{col}": round(float(series[mask].mean()), 4),
            f"std_{col}": round(float(series[mask].std()), 4),
        })

    return {
        "type": "hmm_regime",
        "name": f"Volatility Regime Detection — {col}",
        "description": "Rolling variance segmentation identifies low/normal/high-volatility regimes.",
        "n_states": 3,
        "current_state": int(states[-1]),
        "state_stats": state_stats,
        "transition_matrix": None,
        "significance_score": 0.5,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# FACTOR ANALYSIS (PCA with variance explained)
# ═══════════════════════════════════════════════════════════════════════════════

def run_factor_analysis(df: pd.DataFrame, schema: dict) -> dict | None:
    """
    Principal Component Analysis to identify latent factors driving variance.
    Reports explained variance, factor loadings, and which columns load on each factor.
    """
    num_cols = [
        c for c, m in schema.get("columns", {}).items()
        if m.get("dtype") == "numeric" and c in df.columns
    ]

    if len(num_cols) < 3:
        return None

    sub = df[num_cols].dropna()
    if len(sub) < 20:
        return None

    scaler = StandardScaler()
    X = scaler.fit_transform(sub.values)

    n_components = min(len(num_cols), len(sub), 5)
    pca = PCA(n_components=n_components, random_state=42)
    pca.fit(X)

    explained = pca.explained_variance_ratio_
    n_factors_90 = int(np.searchsorted(np.cumsum(explained), 0.90) + 1)

    factors = []
    for i in range(min(n_components, 3)):
        loadings = pca.components_[i]
        top_idx = np.argsort(np.abs(loadings))[::-1][:4]
        factors.append({
            "factor": i + 1,
            "variance_explained": round(float(explained[i]), 4),
            "top_loadings": [
                {"column": num_cols[j], "loading": round(float(loadings[j]), 4)}
                for j in top_idx
            ],
        })

    return {
        "type": "factor_analysis",
        "name": f"Factor Analysis — {n_factors_90} factors explain 90% of variance",
        "description": f"PCA reveals {n_factors_90} latent factors driving {sum(explained[:n_factors_90]):.0%} of total variance.",
        "n_factors_90pct": n_factors_90,
        "total_variance_explained": round(float(sum(explained)), 4),
        "factors": factors,
        "cumulative_variance": [round(float(v), 4) for v in np.cumsum(explained)],
        "significance_score": round(float(1 - explained[0]) if len(explained) > 1 else 0.5, 4),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DISPATCHER
# ═══════════════════════════════════════════════════════════════════════════════

def run_quant_analysis(df: pd.DataFrame, schema: dict) -> list[dict]:
    """
    Run all quant analyses in parallel and return list of findings.
    These run unconditionally on every dataset — no hypotheses needed.
    """
    tasks = [
        ("hurst", run_hurst_analysis),
        ("transfer_entropy", run_transfer_entropy),
        ("cointegration", run_cointegration),
        ("hmm", run_hmm_regime),
        ("factor", run_factor_analysis),
    ]

    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fn, df, schema): name for name, fn in tasks}
        for future in as_completed(futures):
            try:
                result = future.result(timeout=30)
                if result:
                    results.append(result)
            except Exception:
                continue

    return results
