"""Log parsing: CSV/JSON -> normalized [{ts, service, level, message}]."""
import io, json, re
from collections import Counter
import pandas as pd

LEVELS = {"DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"}

class LogParseError(ValueError):
    pass

def _norm(df: pd.DataFrame) -> list[dict]:
    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = {"timestamp", "message"} - set(df.columns)
    if missing:
        raise LogParseError(f"Missing required column(s): {', '.join(sorted(missing))}. "
                            "Expected: timestamp, service, level, message.")
    df["ts"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    if df["ts"].isna().all():
        raise LogParseError("No valid timestamps found. Use ISO-8601 like 2025-01-01T10:00:00Z.")
    df = df.dropna(subset=["ts"]).sort_values("ts")
    out = []
    for _, r in df.iterrows():
        lvl = str(r.get("level") or "INFO").upper()
        lvl = {"WARNING": "WARN", "FATAL": "CRITICAL"}.get(lvl, lvl)
        out.append({"ts": r["ts"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "service": str(r.get("service") or "unknown"),
                    "level": lvl if lvl in LEVELS else "INFO",
                    "message": "" if pd.isna(r["message"]) else str(r["message"])})
    return out

def parse_logs(filename: str, data: bytes) -> list[dict]:
    if not data:
        raise LogParseError("The uploaded file is empty.")
    if len(data) > 5 * 1024 * 1024:
        raise LogParseError("File too large (limit 5 MB).")
    name = (filename or "").lower()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise LogParseError("File must be UTF-8 text.")
    if name.endswith(".csv"):
        try:
            return _norm(pd.read_csv(io.StringIO(text)))
        except LogParseError:
            raise
        except Exception as e:
            raise LogParseError(f"Invalid CSV: {e}")
    if name.endswith(".json"):
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as e:
            raise LogParseError(f"Invalid JSON: {e}")
        if isinstance(obj, dict):
            obj = obj.get("logs")
        if not isinstance(obj, list) or not obj:
            raise LogParseError('JSON must be a non-empty list of log objects (or {"logs": [...]}).')
        return _norm(pd.DataFrame(obj))
    raise LogParseError("Unsupported file type. Upload a .csv or .json file.")

def summarize_logs(logs: list[dict]) -> dict:
    """Group repeated error patterns; error frequency per minute."""
    errs = [l for l in logs if l["level"] in ("ERROR", "CRITICAL")]
    pat = lambda m: re.sub(r"\d+(\.\d+)?", "N", m)[:120]
    groups = Counter((l["service"], pat(l["message"])) for l in errs)
    per_min = Counter(l["ts"][:16] for l in errs)
    return {"error_count": len(errs),
            "patterns": [{"service": s, "pattern": p, "count": c} for (s, p), c in groups.most_common(8)],
            "error_frequency": [{"minute": k, "errors": v} for k, v in sorted(per_min.items())],
            "services_with_errors": sorted({l["service"] for l in errs})}
