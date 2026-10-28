"""Anomaly detection: per-metric baseline z-scores + Isolation Forest over all metrics."""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

METRICS = ["cpu", "memory", "latency", "error_rate", "db_conn"]
F = "%Y-%m-%dT%H:%M:%SZ"

def detect_anomalies(metrics: list[dict]) -> dict:
    if len(metrics) < 10:
        return {"sufficient_data": False, "metrics": {}, "order": [], "anomalous_points": [],
                "note": "At least 10 metric points are needed for anomaly detection."}
    df = pd.DataFrame(metrics)
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce", utc=True)
    df = df.dropna(subset=["ts"]).sort_values("ts").reset_index(drop=True)
    cols = [c for c in METRICS if c in df.columns]
    df[cols] = df[cols].apply(pd.to_numeric, errors="coerce").ffill().bfill().fillna(0)  # missing values
    base_n = max(5, int(len(df) * 0.3))
    result = {}
    for c in cols:
        base = df[c].iloc[:base_n]
        mu, sd = base.mean(), max(base.std(), 1e-6, abs(base.mean()) * 0.02)
        z = (df[c] - mu) / sd
        hot = z > 3
        sustained = hot & (hot.shift(-1, fill_value=False) | hot.shift(1, fill_value=False))
        if sustained.any():
            i = int(np.argmax(sustained.values))
            result[c] = {"first_anomaly_ts": df["ts"][i].strftime(F), "baseline": round(float(mu), 2),
                         "peak": round(float(df[c].max()), 2), "max_z": round(float(z.max()), 1),
                         "slope_per_point": round(float(np.polyfit(range(len(df)), df[c], 1)[0]), 3)}
    model = IsolationForest(n_estimators=100, contamination=0.1, random_state=42).fit(df[cols])
    scores, flags = -model.score_samples(df[cols]), model.predict(df[cols]) == -1
    pts = [{"ts": df["ts"][i].strftime(F), "score": round(float(scores[i]), 3)} for i in range(len(df)) if flags[i]]
    return {"sufficient_data": True, "metrics": result, "order": sorted(result, key=lambda k: result[k]["first_anomaly_ts"]),
            "anomalous_points": pts, "model": "IsolationForest(random_state=42) + baseline z-score"}
