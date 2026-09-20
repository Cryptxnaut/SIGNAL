import pandas as pd
import numpy as np
from typing import Any

TIME_KEYWORDS = {"time", "date", "timestamp", "ts", "datetime", "created", "updated", "at"}

# Domain hint keywords — just for fingerprinting, full detection is in domain_detector
_DOMAIN_HINT_KEYWORDS = [
    "temperature", "temp", "pressure", "humidity", "wind", "patient", "diagnosis",
    "treatment", "hospital", "taxi", "trip", "fare", "pickup", "price", "return",
    "volume", "stock", "gene", "sequence", "energy", "power", "electricity",
    "event", "sentiment", "material", "crystal",
]


def _has_time_keyword(col_name: str) -> bool:
    col_lower = col_name.lower()
    return any(kw in col_lower for kw in TIME_KEYWORDS)


def _is_monotonic_increasing(series: pd.Series) -> bool:
    clean = series.dropna()
    if len(clean) < 2:
        return False
    return bool(clean.is_monotonic_increasing)


def _is_id_column(series: pd.Series, col_name: str) -> bool:
    """Detect likely ID columns — monotonically increasing integers or very high cardinality."""
    col_lower = col_name.lower()
    # Name-based heuristics
    if any(kw in col_lower for kw in ["_id", "id", "index", "key", "rownum", "row_num"]):
        return True
    if not pd.api.types.is_integer_dtype(series):
        return False
    clean = series.dropna()
    if len(clean) < 2:
        return False
    # High cardinality + monotonically increasing integer = likely ID
    if clean.is_monotonic_increasing and clean.nunique() == len(clean):
        return True
    # Near-unique high-cardinality integer
    if clean.nunique() / len(clean) > 0.95 and len(clean) > 50:
        return True
    return False


def _is_potential_target(series: pd.Series) -> bool:
    """Detect likely target/label columns — binary or low-cardinality numeric."""
    if not pd.api.types.is_numeric_dtype(series):
        return False
    clean = series.dropna()
    if len(clean) < 2:
        return False
    unique_vals = clean.nunique()
    val_set = set(clean.unique())
    # Binary 0/1
    if unique_vals == 2 and val_set.issubset({0, 1, 0.0, 1.0}):
        return True
    # Low-cardinality integer (likely class labels)
    if unique_vals <= 10 and pd.api.types.is_integer_dtype(series):
        return True
    return False


def infer_schema(df: pd.DataFrame) -> dict:
    columns = {}
    n_time_series = 0
    n_numeric = 0
    n_categorical = 0
    n_datetime = 0

    for col in df.columns:
        series = df[col]
        null_pct = float(series.isna().mean())
        col_info: dict[str, Any] = {"null_pct": null_pct}

        # Try datetime first
        if pd.api.types.is_datetime64_any_dtype(series):
            col_info["dtype"] = "datetime"
            n_datetime += 1
            clean = series.dropna()
            if len(clean) > 0:
                col_info["range"] = f"{clean.min()} — {clean.max()}"
                try:
                    inferred = pd.infer_freq(clean)
                    col_info["inferred_freq"] = inferred if inferred else "unknown"
                except Exception:
                    col_info["inferred_freq"] = "unknown"
            else:
                col_info["range"] = "N/A"
                col_info["inferred_freq"] = "unknown"

        elif pd.api.types.is_bool_dtype(series):
            col_info["dtype"] = "boolean"

        elif pd.api.types.is_numeric_dtype(series):
            clean = series.dropna()
            col_info["dtype"] = "numeric"
            col_info["min"] = float(clean.min()) if len(clean) > 0 else None
            col_info["max"] = float(clean.max()) if len(clean) > 0 else None
            col_info["mean"] = float(clean.mean()) if len(clean) > 0 else None
            col_info["std"] = float(clean.std()) if len(clean) > 1 else 0.0

            is_ts = _is_monotonic_increasing(series) or _has_time_keyword(col)
            col_info["is_time_series"] = is_ts
            if is_ts:
                n_time_series += 1

            # ID and target detection
            col_info["is_id"] = _is_id_column(series, col)
            col_info["is_potential_target"] = _is_potential_target(series) and not col_info["is_id"]
            n_numeric += 1

        else:
            # Try to parse as datetime
            try:
                parsed = pd.to_datetime(series, infer_datetime_format=True)
                if parsed.notna().sum() > len(series) * 0.8:
                    col_info["dtype"] = "datetime"
                    n_datetime += 1
                    clean = parsed.dropna()
                    if len(clean) > 0:
                        col_info["range"] = f"{clean.min()} — {clean.max()}"
                        try:
                            inferred = pd.infer_freq(clean)
                            col_info["inferred_freq"] = inferred if inferred else "unknown"
                        except Exception:
                            col_info["inferred_freq"] = "unknown"
                    else:
                        col_info["range"] = "N/A"
                        col_info["inferred_freq"] = "unknown"
                    columns[col] = col_info
                    continue
            except Exception:
                pass

            # Categorical or text
            nunique = series.nunique()
            n_total = len(series)
            if nunique <= 50 or (n_total > 0 and nunique / n_total < 0.5):
                col_info["dtype"] = "categorical"
                col_info["cardinality"] = int(nunique)
                top = series.value_counts().head(5)
                col_info["top_values"] = [str(v) for v in top.index.tolist()]
                n_categorical += 1
            else:
                col_info["dtype"] = "text"
                col_info["cardinality"] = int(nunique)

        columns[col] = col_info

    # Domain hints: column names matching domain keywords
    all_col_names = " ".join(df.columns.tolist()).lower()
    domain_hints = [
        col for col in df.columns
        if any(kw in col.lower() for kw in _DOMAIN_HINT_KEYWORDS)
    ]

    data_fingerprint = {
        "n_rows": len(df),
        "n_numeric": n_numeric,
        "n_categorical": n_categorical,
        "n_datetime": n_datetime,
        "n_time_series": n_time_series,
        "estimated_domain_hints": domain_hints[:10],
    }

    return {
        "columns": columns,
        "n_columns": len(columns),
        "n_time_series": n_time_series,
        "n_rows": len(df),
        "data_fingerprint": data_fingerprint,
    }
