"""Finding ranker — composite scoring with effect size and novelty."""


def _effect_size_score(finding: dict) -> float:
    """Extract effect size signal from finding."""
    ftype = finding.get("type", "")
    if ftype == "correlation":
        top = finding.get("top_correlation", {})
        r = abs(top.get("r", 0))
        d = top.get("cohens_d", 0)
        return min(1.0, (r + d / 4) / 1.5)
    if ftype == "mutual_info":
        top = finding.get("top_predictor", {})
        mi = top.get("mutual_info", 0)
        return min(1.0, mi / 2.0)
    if ftype == "anomaly":
        return min(1.0, finding.get("anomaly_rate", 0) * 5)
    if ftype == "trend":
        pct = abs(finding.get("trend_change_pct", 0))
        season = finding.get("seasonality_strength", 0)
        return min(1.0, (pct / 100 + season) / 2)
    if ftype == "leading_indicator":
        top = finding.get("top_indicator", {})
        p = top.get("p_value", 1.0)
        return max(0.0, 1 - p)
    if ftype == "regime_change":
        n = finding.get("n_changepoints", 0)
        return min(1.0, n / 10)
    if ftype == "clustering":
        return max(0.0, finding.get("silhouette_score", 0))
    return 0.0


def _novelty_bonus(finding: dict) -> float:
    """Rare finding types get a small bonus to surface diverse insights."""
    bonuses = {
        "mutual_info": 0.05,    # non-linear, often missed
        "leading_indicator": 0.04,
        "regime_change": 0.03,
        "clustering": 0.02,
        "trend": 0.01,
        "correlation": 0.0,
        "anomaly": 0.0,
    }
    return bonuses.get(finding.get("type", ""), 0.0)


def rank_findings(stats_results: list) -> list:
    """Rank findings by composite score: significance + effect size + novelty."""
    if not stats_results:
        return []

    scored = []
    for finding in stats_results:
        sig = finding.get("significance_score", 0.0)
        effect = _effect_size_score(finding)
        novelty = _novelty_bonus(finding)
        composite = 0.5 * sig + 0.4 * effect + 0.1 * novelty
        scored.append((composite, finding))

    scored.sort(key=lambda x: -x[0])

    results = []
    for rank, (score, finding) in enumerate(scored, 1):
        f = dict(finding)
        f["rank"] = rank
        f["composite_score"] = round(score, 4)
        results.append(f)

    return results
