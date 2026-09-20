# SIGNAL — Theory & Methodology
**HackMIT 2026 · Voloridge "Signal in the Noise" Track**

---

## Overview

SIGNAL is a full-stack quantitative analysis platform that applies production-grade financial signal research methods to arbitrary datasets. The core thesis: most tools find *statistically significant* patterns; we additionally test whether those patterns are *genuinely reliable* — a distinction that separates academic curiosity from actionable intelligence.

Every finding SIGNAL produces passes through three tiers of validation before being presented:

1. **Detection** — find the pattern using appropriate statistical methods
2. **Quantification** — measure its strength, direction, and effect size
3. **Quality scoring** — test whether it holds out-of-sample, survives bootstrap resampling, and persists over time

---

## Architecture

```
Upload / URL Load
      │
      ▼
Schema Inference ──► Domain Detection
      │                     │
      ▼                     ▼
Data Quality Score    Domain-Aware LLM
      │                     │
      ▼                     ▼
Hypothesis Generation (Qwen2.5:72b)
      │
      ├──────────────────────┐
      ▼                      ▼
Standard Stats Pipeline   Quant Pipeline (parallel)
  • Pearson/Spearman        • Hurst Exponent
  • Mutual Information      • Transfer Entropy
  • IsolationForest         • Cointegration
  • STL Trend               • Hidden Markov Model
  • Granger Causality       • Factor Analysis
  • K-Means Clustering
      │
      ▼
Signal Quality Scoring
  • Walk-Forward Validation
  • Bootstrap Confidence Intervals
  • Rolling Stability
      │
      ▼
Composite Ranking + LLM Explanations (batched)
      │
      ▼
Model Training (LightGBM, domain-aware)
+ SHAP Feature Importance
      │
      ▼
Adversarial Stress Testing
      │
      ▼
Structured Report + Consultant Chat
```

---

## Statistical Methods

### 1. Correlation Analysis

**Pearson r** measures linear association. We complement it with:

- **Spearman ρ** — rank-based, captures monotonic but non-linear relationships
- **Partial correlation** — controls for confounding variables by residualising X and Y on a set of control variables before computing correlation
- **Cohen's d** — effect size via median-split comparison, independent of sample size

The distinction between *statistical significance* (p-value) and *practical significance* (effect size) is critical. A p < 0.001 finding with Cohen's d = 0.05 is real but useless in practice.

### 2. Mutual Information

**Mutual Information (MI)** measures the reduction in uncertainty about Y given knowledge of X, using Shannon entropy:

```
MI(X; Y) = H(X) + H(Y) - H(X, Y)
```

Unlike Pearson r, MI captures **non-linear and non-monotonic** relationships. We use scikit-learn's `mutual_info_regression` / `mutual_info_classif` with k-NN entropy estimation.

We also report a **nonlinearity score** = MI - |Pearson r|, which surfaces signals that linear methods would miss entirely. This is a direct operationalisation of "finding the signal in the noise."

### 3. Granger Causality

A time series X **Granger-causes** Y if past values of X significantly improve the prediction of Y beyond Y's own past values. Tested via the F-statistic on VAR residuals:

```
H₀: The coefficients on lagged X are jointly zero in the VAR(p) for Y
```

We test lags 1–12 (up from the standard 4) to capture slow-moving economic and climate effects. The Granger causality test is a *predictive* (not structural) causal test — it identifies forecasting relationships, not necessarily causal mechanisms.

### 4. Transfer Entropy

Transfer entropy is a **model-free, nonparametric** measure of directed information flow:

```
TE(X→Y) = H(Yₜ | Yₜ₋₁) − H(Yₜ | Yₜ₋₁, Xₜ₋₁)
```

Where H is Shannon entropy. TE captures non-linear causal influences that Granger causality misses because Granger is parametric (assumes linear VAR structure). We implement TE via histogram binning with equal-frequency discretisation.

**Key property:** TE is asymmetric — TE(X→Y) ≠ TE(Y→X). The net flow direction identifies which variable is the *driver* and which is *driven*, providing directional signal priority for modelling.

### 5. Hurst Exponent

The Hurst exponent H characterises the long-range dependence of a time series via Rescaled Range (R/S) analysis:

```
E[R(n)/S(n)] ~ C · n^H   as n → ∞
```

Where R(n) is the range and S(n) is the standard deviation over a window of size n.

| H | Regime | Interpretation |
|---|--------|----------------|
| H < 0.5 | Anti-persistent | Mean-reverting; shocks reverse → use contrarian signals |
| H ≈ 0.5 | Random walk | No exploitable signal; Brownian motion |
| H > 0.5 | Persistent | Trending; shocks persist → use momentum signals |

This is the **first thing a quant asks** before deciding on a signal strategy. A correlation found in a random-walk series (H ≈ 0.5) is much more likely to be spurious than one in a persistent series.

### 6. Cointegration

Two non-stationary time series X and Y are **cointegrated** if there exists a linear combination β such that:

```
Zₜ = Yₜ − β·Xₜ   is stationary
```

Despite X and Y individually having unit roots (I(1)), their spread Z is I(0) — it mean-reverts. This is the statistical foundation of:
- **Pairs trading** in equities
- **Purchasing power parity** in FX
- **Long-horizon forecasting** in macroeconomics

We test using the Engle-Granger two-step procedure and estimate:
- The **hedge ratio β** via OLS
- The **half-life of mean reversion** via Ornstein-Uhlenbeck fitting:

```
dZₜ = κ(μ − Zₜ)dt + σdWₜ
Half-life = ln(2) / κ
```

A short half-life (e.g., 5 periods) indicates a fast-reverting spread — highly exploitable. A long half-life (e.g., 200 periods) indicates a slow co-movement — useful for long-horizon hedging.

### 7. Hidden Markov Model Regime Detection

A **Gaussian HMM** with k states models a time series as arising from a latent Markov chain:

```
P(Xₜ | Sₜ = k) = N(μₖ, Σₖ)
P(Sₜ | Sₜ₋₁) = A   (transition matrix)
```

We fit the model via Baum-Welch (EM algorithm) and select k via BIC. Each hidden state represents a distinct **data regime** — low-volatility, high-volatility, trending, etc.

**Why this matters:** Many correlations are regime-conditional. A relationship that holds strongly in one regime may be zero or even reversed in another. Regime-aware analysis avoids the mistake of averaging over structurally different periods.

### 8. Factor Analysis (PCA)

Principal Component Analysis decomposes the covariance matrix of numeric columns into orthogonal factors:

```
X = F·L' + ε
```

Where F are the latent factors and L are the loadings. We report:
- **Explained variance ratio** per factor
- **Number of factors** needed to explain 90% of variance (dimensionality of the signal space)
- **Top column loadings** per factor (which variables co-move)

This identifies whether a dataset has **one dominant factor** (e.g., a market beta in financial data) or **multiple independent signals**, which directly informs model architecture decisions.

---

## Signal Quality Framework

### The Problem with p-values

A p-value tests whether an effect is non-zero — it does **not** test whether the effect is stable, reproducible, or economically meaningful. In finance, the majority of published "significant" factors fail out-of-sample (the factor zoo problem, Harvey et al. 2016).

SIGNAL computes a **Signal Quality Score (SQS)** for every correlation finding:

```
SQS = 0.35 · OOS_score + 0.35 · Bootstrap_score + 0.30 · Stability_score
```

### Component 1: Walk-Forward Validation (OOS Score)

Train on an expanding window of data, test on the next unseen slice. Repeat n_splits times:

```
Window 1: train [0, T₁], test [T₁, T₂]
Window 2: train [0, T₂], test [T₂, T₃]
...
```

We report: mean OOS correlation, standard deviation, fraction of windows with correct sign, and in-sample vs OOS degradation. A finding that holds OOS with low degradation is far more trustworthy than one with perfect in-sample fit but poor OOS performance.

### Component 2: Bootstrap Confidence Intervals (Bootstrap Score)

Bootstrap the dataset 500 times and compute the correlation distribution. Report the 95% CI:

- **CI excludes zero** → signal is robust to sampling variation
- **CI width** → precision of the estimate; narrow = reliable

Unlike asymptotic CIs (which assume normality), bootstrap CIs are valid for any distribution and any statistic.

### Component 3: Rolling Stability (Stability Score)

Compute the correlation in 10 equal windows across the time series. Report:

- **Mean and std of window correlations** — high mean, low std = persistent signal
- **Sign flips** — how many times the sign reverses across windows
- **Trend** — is the signal strengthening or weakening over time?

A signal with three sign reversals is likely regime-conditional or spurious. A signal with consistent sign and magnitude across all windows is genuinely reliable.

### SQS Grading

| SQS | Grade | Interpretation |
|-----|-------|----------------|
| > 0.70 | A | High-confidence signal — robust OOS, CI excludes zero, stable |
| 0.50–0.70 | B | Good signal — some degradation but generally reliable |
| 0.35–0.50 | C | Weak signal — use with caution, high uncertainty |
| < 0.35 | D | Likely spurious — do not act on this finding |

---

## Model Architecture

### Problem Type Auto-Detection

SIGNAL automatically selects the appropriate learning objective:

| Target characteristics | Problem type | Metric |
|---|---|---|
| Binary {0, 1} | Classification | AUC-ROC + PR-AUC |
| Integer ≤ 15 unique | Multi-class | Macro F1 |
| Continuous | Regression | R², RMSE, MAE, MAPE |

### LightGBM Configuration

We use gradient-boosted trees (LightGBM) because:
- Handles mixed types, missing values, and skewed distributions natively
- SHAP values are exact (not approximate) via TreeExplainer
- `is_unbalance=True` handles class imbalance without manual reweighting
- Early stopping on validation set prevents overfitting

For regression we use `objective="regression_l1"` (MAE loss) rather than L2 because MAE is more robust to outliers — critical for real-world datasets with measurement errors.

### Time Series Feature Engineering

When a time series index is detected, SIGNAL automatically adds **lag features**:

```python
col_lag1 = col.shift(1)   # most recent past value
col_lag2 = col.shift(2)   # 2 periods ago
col_lag3 = col.shift(3)   # 3 periods ago
```

This allows the model to learn temporal patterns (momentum, mean reversion) that would be invisible to a cross-sectional model.

### SHAP Feature Importance

SHapley Additive exPlanations decompose each prediction into per-feature contributions:

```
f(x) = φ₀ + Σᵢ φᵢ(xᵢ)
```

Where φᵢ is the marginal contribution of feature i, computed over all possible feature orderings (Shapley values from cooperative game theory). This gives **exact, consistent** feature attributions — not the impurity-based importances that can be misleading in tree models.

---

## LLM Integration

SIGNAL uses **Qwen2.5:72b** running locally on an ASUS GX10 (Blackwell GPU) via Ollama.

### Domain-Aware Prompting

After schema inference, we detect the dataset domain (climate, healthcare, finance, transport, genomics, energy, events, materials) and inject domain-specific system context into every LLM call. A climate scientist prompt produces meteorologically precise explanations; a financial analyst prompt uses appropriate risk and return framing.

### Batch Explanation

Rather than calling the LLM once per finding (5 calls), we batch all top-5 findings into a single structured prompt (1 call), reducing latency by ~80% and providing the model with cross-finding context for more coherent explanations.

### Hypothesis Generation

The LLM generates analysis hypotheses from the schema — specifying which columns to test, which statistical method to apply, and why. This enables **intent-driven analysis**: the same dataset analysed with the intent "find anomalies" vs "find leading indicators" will generate structurally different analysis plans.

---

## Competitive Differentiation

| Capability | Typical hackathon project | SIGNAL |
|---|---|---|
| Correlation | Pearson only | Pearson + Spearman + Partial + Cohen's d |
| Non-linear detection | None | Mutual information |
| Causality | None | Granger + Transfer entropy |
| Signal reliability | p-value only | Walk-forward + Bootstrap + Rolling stability |
| Time series regime | None | HMM + Hurst exponent |
| Shared trends | None | Cointegration + half-life |
| Dimensionality | None | PCA factor analysis |
| Model | Single model | Domain-adapted LightGBM with auto problem type |
| Explainability | None | Exact SHAP values |
| LLM | Cloud API | Local 72B model, domain-aware, batched |
| Large files | Crash | Sampled to 50k rows on upload |
| Cross-dataset | Not applicable | URL loader for any public dataset |

### The Key Insight

Voloridge's theme is "Signal in the Noise." Most submissions will demonstrate they can **find signals**. SIGNAL demonstrates it can also **distinguish genuine signals from noise** — through Signal Quality Scoring, out-of-sample validation, and bootstrap testing. This is the intellectual contribution that mirrors what production quant research actually looks like.

---

## Implementation Notes

- **Parallel execution**: stats pipeline, quant pipeline, and model training all run concurrently via `asyncio.gather` + `ThreadPoolExecutor`. Total analysis time is bounded by the slowest component, not their sum.
- **No external data dependencies**: all methods use scipy, statsmodels, sklearn, and lightweight implementations. Transfer entropy is implemented from scratch to avoid brittle dependencies.
- **Graceful degradation**: if `hmmlearn` is not installed, regime detection falls back to variance-based segmentation. If Ollama is offline, all statistical analysis still runs; only LLM explanations are skipped.
- **Memory safety**: datasets >100MB are sampled to 50k rows on upload. Models are trained on ≤20k rows with stratified sampling for classifiers.

---

*Built for HackMIT 2026 — Voloridge "Signal in the Noise" Track*
