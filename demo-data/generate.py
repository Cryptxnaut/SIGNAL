"""
SIGNAL demo data generator.
Generates climate_sample.csv and sensor_stream.csv.
Run: python generate.py
"""
import numpy as np
import pandas as pd
from pathlib import Path

OUT_DIR = Path(__file__).parent


def generate_demo_data():
    rng = np.random.default_rng(seed=42)

    # ── climate_sample.csv ────────────────────────────────────────────────────
    n = 500
    timestamps = pd.date_range("2023-01-01", periods=n, freq="h")
    t = np.arange(n)

    # Seasonal temperature
    temperature_c = (
        15
        + 10 * np.sin(2 * np.pi * t / (365 * 24))
        + rng.normal(0, 2, n)
    )

    # Extreme event: ~50 events, some clustered
    extreme_event = np.zeros(n, dtype=int)
    # Scattered single events
    single_events = rng.choice(n, size=30, replace=False)
    extreme_event[single_events] = 1
    # Clustered events (5 clusters of 4)
    cluster_centers = rng.choice(n, size=5, replace=False)
    for c in cluster_centers:
        for offset in range(4):
            idx = min(c + offset, n - 1)
            extreme_event[idx] = 1

    # Pressure: mean 1013 hPa, drops ~30 hPa during extreme events
    # Use tighter base std and larger drop to push correlation toward -0.7
    base_pressure = rng.normal(1013, 5, n)
    pressure_hpa = base_pressure - extreme_event * rng.uniform(25, 35, n)

    # Humidity: higher during extreme events
    humidity_pct = np.where(
        extreme_event,
        rng.uniform(65, 90, n),
        rng.uniform(40, 70, n),
    ).clip(0, 100)

    # Wind speed: higher during extreme events
    wind_speed_ms = np.where(
        extreme_event,
        rng.uniform(5, 15, n),
        rng.uniform(0, 6, n),
    ).clip(0, 20)

    # Rainfall: spikes during extreme events
    rainfall_mm = np.where(
        extreme_event,
        rng.uniform(10, 50, n),
        rng.exponential(0.5, n),
    ).clip(0, 100)

    climate_df = pd.DataFrame({
        "timestamp": timestamps,
        "temperature_c": np.round(temperature_c, 2),
        "pressure_hpa": np.round(pressure_hpa, 2),
        "humidity_pct": np.round(humidity_pct, 1),
        "wind_speed_ms": np.round(wind_speed_ms, 2),
        "rainfall_mm": np.round(rainfall_mm, 2),
        "extreme_event": extreme_event,
    })

    # Verify correlation
    r = np.corrcoef(pressure_hpa, extreme_event.astype(float))[0, 1]
    print(f"pressure_hpa vs extreme_event Pearson r = {r:.4f}")

    climate_path = OUT_DIR / "climate_sample.csv"
    climate_df.to_csv(climate_path, index=False)
    print(f"Wrote {len(climate_df)} rows to {climate_path}")

    # ── sensor_stream.csv ──────────────────────────────────────────────────────
    n_s = 300
    sensor_timestamps = pd.date_range("2024-01-01", periods=n_s, freq="s")
    t_s = np.arange(n_s)

    channels = {}
    for i in range(1, 6):
        base = np.sin(t_s * (0.1 + i * 0.03) + i) * 20 + 50
        noise = rng.normal(0, 3, n_s)
        channels[f"channel_{i}"] = base + noise

    # Inject anomalies at rows 150-155 and 280-285
    for ch_data in channels.values():
        for idx in range(150, 156):
            ch_data[idx] *= rng.uniform(3, 5)
        for idx in range(280, 286):
            ch_data[idx] *= rng.uniform(3, 5)

    sensor_df = pd.DataFrame({"timestamp": sensor_timestamps})
    for ch_name, ch_data in channels.items():
        sensor_df[ch_name] = np.round(ch_data, 3)

    sensor_path = OUT_DIR / "sensor_stream.csv"
    sensor_df.to_csv(sensor_path, index=False)
    print(f"Wrote {len(sensor_df)} rows to {sensor_path}")

    return climate_df, sensor_df


if __name__ == "__main__":
    generate_demo_data()
    print("Demo data generation complete.")
