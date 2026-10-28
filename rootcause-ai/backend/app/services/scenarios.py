"""Deterministic demo scenarios (seeded RNG -> identical output every run)."""
import random
from datetime import datetime, timedelta

START = datetime(2025, 3, 14, 10, 0, 0)
fmt = lambda t: t.strftime("%Y-%m-%dT%H:%M:%SZ")

def _series(seed, n, fn):
    rnd, pts = random.Random(seed), []
    for i in range(n):
        p = dict(cpu=35 + rnd.uniform(-3, 3), memory=52 + rnd.uniform(-2, 2), latency=120 + rnd.uniform(-10, 10),
                 error_rate=0.5 + rnd.uniform(0, 0.3), db_conn=40 + rnd.uniform(-4, 4))
        fn(i, p, rnd)
        pts.append({"ts": fmt(START + timedelta(minutes=i)), **{k: round(v, 2) for k, v in p.items()}})
    return pts

def _log(i, svc, lvl, msg):
    return {"ts": fmt(START + timedelta(minutes=i)), "service": svc, "level": lvl, "message": msg}

def _db(i, p, r):
    if i >= 20: p["db_conn"] = min(100, 40 + (i - 20) * 6.5)
    if i >= 26: p["latency"] = 120 + (i - 25) * 400 + r.uniform(0, 50)
    if i >= 28: p["error_rate"] = 2 + (i - 27) * 3

def _mem(i, p, r):
    if i >= 8: p["memory"] = 52 + i * 0.85 + r.uniform(-1, 1)
    if i >= 35: p["latency"] = 120 + (i - 34) * 90; p["error_rate"] = 1 + (i - 34) * 1.8

def _cfg(i, p, r):
    if i >= 22: p["error_rate"] = 25 + r.uniform(0, 5); p["latency"] = 200 + r.uniform(0, 30)

SCENARIOS = {
 "db_pool": {"title": "API latency and timeouts (DB pool exhaustion)", "service": "api-gateway", "severity": "critical",
   "initial_condition": "All services healthy; DB connection usage ~40%, API latency ~120 ms.",
   "expected_anomaly": "db_conn rises first, then latency, then error rate.",
   "description": "API response time rose to 5 seconds with request timeouts.",
   "error_message": "TimeoutError: upstream order-service did not respond within 5000ms",
   "metrics": lambda: _series(1, 40, _db),
   "logs": lambda: [_log(5, "api-gateway", "INFO", "Healthy"),
        _log(24, "postgres-db", "WARN", "Connection pool usage at 85%"),
        _log(27, "order-service", "ERROR", "Connection pool exhausted: timeout waiting for connection"),
        _log(28, "api-gateway", "ERROR", "TimeoutError: upstream order-service did not respond within 5000ms"),
        _log(29, "order-service", "ERROR", "Connection pool exhausted: timeout waiting for connection"),
        _log(30, "api-gateway", "ERROR", "TimeoutError: upstream order-service did not respond within 5000ms")],
   "events": lambda: [{"ts": fmt(START - timedelta(days=2)), "type": "deployment", "description": "order-service v2.3 (unrelated UI change)"}]},
 "memory_leak": {"title": "Memory climbing then service instability", "service": "order-service", "severity": "critical",
   "initial_condition": "Memory ~52%, stable.", "expected_anomaly": "memory rises continuously; later latency and errors.",
   "description": "Order service memory has grown for 40 minutes; pods restarting.",
   "error_message": "java.lang.OutOfMemoryError: Java heap space",
   "metrics": lambda: _series(2, 45, _mem),
   "logs": lambda: [_log(20, "order-service", "WARN", "GC overhead high: heap 78%"),
        _log(34, "order-service", "ERROR", "java.lang.OutOfMemoryError: Java heap space"),
        _log(38, "order-service", "ERROR", "Container killed (OOM); restart count 2"),
        _log(40, "api-gateway", "ERROR", "order-service unhealthy: restart loop")],
   "events": lambda: []},
 "bad_config": {"title": "Elevated errors after configuration change", "service": "auth-service", "severity": "critical",
   "initial_condition": "Error rate under 1%.", "expected_anomaly": "error_rate jumps right after the config change.",
   "description": "auth-service returns errors; dependent services fail.",
   "error_message": "401 Unauthorized: invalid config value JWT_ISSUER",
   "metrics": lambda: _series(3, 40, _cfg),
   "logs": lambda: [_log(22, "auth-service", "ERROR", "Invalid config value JWT_ISSUER; rejecting tokens"),
        _log(23, "auth-service", "ERROR", "401 Unauthorized: invalid config value JWT_ISSUER"),
        _log(24, "order-service", "ERROR", "auth-service returned 401"),
        _log(25, "api-gateway", "ERROR", "auth-service returned 401")],
   "events": lambda: [{"ts": fmt(START + timedelta(minutes=21)), "type": "config_change", "description": "JWT_ISSUER changed in auth-service config"}]},
}

def build(key: str) -> dict:
    s = SCENARIOS[key]
    d = {k: s[k] for k in ("title", "service", "severity", "description", "error_message")}
    d.update({k: s[k]() for k in ("metrics", "logs", "events")})
    return d

def info():
    return [{"key": k, "title": v["title"], "initial_condition": v["initial_condition"],
             "expected_anomaly": v["expected_anomaly"]} for k, v in SCENARIOS.items()]

THRESH = {"cpu": 85, "memory": 85, "latency": 1000, "error_rate": 5, "db_conn": 90}

def live_tick(t: int, failing_since):
    rnd = random.Random(t)
    p = dict(cpu=35 + rnd.uniform(-5, 5), memory=52 + rnd.uniform(-3, 3), latency=120 + rnd.uniform(-15, 15),
             error_rate=0.5 + rnd.uniform(0, .4), db_conn=40 + rnd.uniform(-5, 5))
    if failing_since is not None and t >= failing_since:
        k = t - failing_since
        p["db_conn"] = min(100, 40 + k * 8)
        if k >= 3: p["latency"] = 120 + (k - 2) * 450
        if k >= 4: p["error_rate"] = 1 + (k - 3) * 3
    p = {k: round(v, 2) for k, v in p.items()}
    return {"t": t, "ts": fmt(datetime.utcnow()), **p, "breaches": [k for k, v in p.items() if v >= THRESH[k]], "demo": True}
