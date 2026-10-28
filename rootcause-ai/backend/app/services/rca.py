"""Rule-based root-cause ranking. Findings are SUSPECTED causes; correlation is not proof."""
from datetime import datetime
from .anomaly import detect_anomalies
from .logs import summarize_logs

NOT_CONFIRMED = "Root cause not confirmed. More evidence is required."
F = "%Y-%m-%dT%H:%M:%SZ"

def _has(logs, *words):
    return [l for l in logs if any(w in l["message"].lower() for w in words)]

def _before(an, a, b):
    m = an["metrics"]
    return a in m and b in m and m[a]["first_anomaly_ts"] < m[b]["first_anomaly_ts"]

def _cands(inc, an, logs):
    m, events = an["metrics"], inc.get("events", [])
    deploys = [e for e in events if e.get("type") in ("deployment", "config_change")]
    out = []

    def add(name, parts, affected, impact, investigate, prevent, missing):
        score, total = sum(w for ok, w, _ in parts if ok), sum(w for _, w, _ in parts)
        out.append({"cause": name, "confidence": round(score / total, 2),
                    "supporting_evidence": [d for ok, _, d in parts if ok],
                    "contradicting_evidence": [f"Not observed: {d}" for ok, _, d in parts if not ok][:3],
                    "affected_services": affected, "impact": impact, "recommended_investigation": investigate,
                    "preventive_action": prevent, "missing_evidence": missing,
                    "label": "suspected cause (unverified)"})

    pool = _has(logs, "pool", "too many connections")
    db = m.get("db_conn", {})
    add("Database connection pool exhaustion",
        [(db.get("peak", 0) >= 90, 3, f"DB connection usage peaked at {db.get('peak')}%"),
         (_before(an, "db_conn", "latency"), 3, "DB connection saturation began before API latency rose"),
         (bool(pool), 2, f"{len(pool)} log lines mention pool/connection exhaustion"),
         ("latency" in m, 1, "API latency anomaly present"),
         (not deploys, 1, "No recent deployment that better explains the change")],
        ["postgres-db", "order-service", "api-gateway"], "Requests queue for connections, causing latency and timeouts.",
        ["Compare active vs. max DB connections", "Look for leaked or long-running connections", "Review pool size settings"],
        ["Alert at 80% pool use", "Set pool limits and connection timeouts", "Load-test with realistic concurrency"],
        [] if pool else ["Application logs showing pool errors"])
    mem = m.get("memory", {})
    add("Memory leak",
        [(mem.get("slope_per_point", 0) > 0.2, 3, "Memory grows steadily across the window"),
         (mem.get("peak", 0) >= 85, 2, f"Memory peaked at {mem.get('peak')}%"),
         (bool(_has(logs, "outofmemory", "oom", "gc overhead", "heap")), 3, "Logs mention heap/OOM/GC pressure"),
         (bool(_has(logs, "restart", "unhealthy", "killed")), 1, "Restarts or health failures logged"),
         ("memory" in m and not _before(an, "latency", "memory"), 1, "Memory rose before latency did")],
        [inc["service"]], "Service degrades, then restarts or crashes.",
        ["Take heap profiles over time", "Compare memory growth with release history", "Check unbounded caches/collections"],
        ["Alert on sustained memory slope", "Add soak tests with memory limits", "Track heap growth on dashboards"],
        [] if _has(logs, "heap", "oom") else ["Heap dump or GC logs"])
    cfg = _has(logs, "config", "invalid", "missing env", "401", "403")
    first_err = min((l["ts"] for l in logs if l["level"] in ("ERROR", "CRITICAL")), default=None)
    near = [e for e in deploys if first_err and 0 <= (datetime.strptime(first_err, F) - datetime.strptime(e["ts"], F)).total_seconds() <= 1800]
    err_svcs = sorted({l["service"] for l in logs if l["level"] in ("ERROR", "CRITICAL")})
    add("Incorrect deployment / configuration change",
        [(bool(near), 4, "A deployment/config change happened shortly before the first error"),
         ("error_rate" in m, 2, "Error-rate anomaly detected"),
         (bool(cfg), 2, f"{len(cfg)} log lines mention config/auth problems"),
         (len(err_svcs) > 1, 1, "Errors spread to dependent services"),
         ("cpu" not in m and "memory" not in m, 1, "No resource saturation that would explain it instead")],
        err_svcs or [inc["service"]], "Requests fail in the changed service and in its dependents.",
        ["Diff the latest config/deployment", "Compare error onset with the change time", "Verify via rollback in staging"],
        ["Canary releases", "Config validation in CI", "Alert on post-deploy error-rate jump"],
        [] if deploys else ["Deployment/config event history"])
    cpu = m.get("cpu", {})
    add("CPU overload",
        [(cpu.get("peak", 0) >= 90, 3, f"CPU peaked at {cpu.get('peak')}%"),
         (_before(an, "cpu", "latency"), 3, "CPU rose before latency"),
         (bool(_has(logs, "cpu", "throttl")), 1, "Logs mention CPU/throttling"),
         ("db_conn" not in m, 1, "DB saturation not observed")],
        [inc["service"]], "Slow request handling and timeouts.",
        ["Profile hot code paths", "Check traffic spikes and autoscaling"],
        ["CPU alert at 80%", "Autoscaling policy", "Load tests"], ["Request-rate metrics"])
    net = _has(logs, "network", "dns", "connection reset", "unreachable")
    add("Network latency",
        [(bool(net), 3, f"{len(net)} log lines mention network faults"),
         ("latency" in m, 2, "Latency anomaly present"),
         ("cpu" not in m and "db_conn" not in m, 2, "No CPU/DB saturation observed")],
        [inc["service"]], "Slow or failing inter-service calls.",
        ["Check packet loss/RTT between services", "Check DNS and load-balancer health"],
        ["Synthetic network probes", "Retries with backoff"], ["Network-level metrics"])
    return out

def build_timeline(inc, an, logs):
    tl = []
    for n, k in enumerate(an["order"]):
        mm = an["metrics"][k]
        tl.append({"ts": mm["first_anomaly_ts"], "kind": "observed", "earliest": n == 0,
                   "text": ("First unusual metric: " if n == 0 else "Metric anomaly: ") + f"{k} (baseline {mm['baseline']}, peak {mm['peak']})"})
    errs = [l for l in logs if l["level"] in ("ERROR", "CRITICAL")]
    seen = set()
    for l in errs:
        if l["service"] not in seen:
            tl.append({"ts": l["ts"], "kind": "observed",
                       "text": ("First error" if not seen else "Related service failing") + f" ({l['service']}): {l['message'][:90]}"})
            seen.add(l["service"])
    for e in inc.get("events", []):
        tl.append({"ts": e["ts"], "kind": "observed", "text": f"{e.get('type', 'event')}: {e.get('description', '')}"})
    tl.sort(key=lambda x: x["ts"])
    if inc.get("resolved_at"):
        tl.append({"ts": inc["resolved_at"], "kind": "observed", "text": "Incident marked resolved"})
    if tl:
        tl.append({"ts": tl[-1]["ts"], "kind": "inferred", "text": "Root-cause analysis run (suspected causes, not confirmed)"})
    return tl

def checklist(top):
    if not top:
        return [{"group": "Immediate investigation", "item": "Collect more logs, metrics and deployment history",
                 "reason": "Evidence is insufficient", "evidence": [], "requires_human_review": True}]
    rows = [("Immediate investigation", i) for i in top["recommended_investigation"]]
    rows += [("Corrective action", f"Propose and review a fix for: {top['cause']}"),
             ("Long-term prevention", top["preventive_action"][0]),
             ("Monitoring / alert thresholds", "; ".join(top["preventive_action"][1:]) or "Alert on first anomalous metric"),
             ("Tests", "Add a regression/load test reproducing this scenario")]
    return [{"group": g, "item": i, "reason": f"Addresses suspected cause: {top['cause']}",
             "evidence": top["supporting_evidence"][:3], "requires_human_review": True} for g, i in rows]

def analyze(inc: dict) -> dict:
    logs, metrics = inc.get("logs") or [], inc.get("metrics") or []
    an, summ = detect_anomalies(metrics), summarize_logs(logs)
    cands = sorted(_cands(inc, an, logs), key=lambda c: -c["confidence"])
    ok = (an["sufficient_data"] or bool(logs)) and cands[0]["confidence"] >= 0.5
    kept = [c for c in cands if c["confidence"] > 0.2] if ok else []
    return {"anomalies": an, "log_summary": summ, "candidates": kept,
            "verdict": "Suspected root cause identified (unverified)" if ok else NOT_CONFIRMED,
            "top_cause": kept[0]["cause"] if ok else None, "alternatives": [c["cause"] for c in kept[1:3]],
            "affected_services": sorted(set(kept[0]["affected_services"] if ok else []) | set(summ["services_with_errors"])),
            "timeline": build_timeline(inc, an, logs), "checklist": checklist(kept[0] if ok else None),
            "disclaimer": "Findings are correlations and suspected causes, not proven causation."}
