import csv, io, json, os
from datetime import datetime
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query
from fastapi.responses import Response
from sqlalchemy import or_
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import Incident, Analysis
from ..schemas.schemas import IncidentCreate, MetricsIn, ResolveIn, LivePoint
from ..services import logs as logsvc, rca, ai, scenarios
from ..services.anomaly import detect_anomalies

router = APIRouter(prefix="/api")
F = "%Y-%m-%dT%H:%M:%SZ"

def _inc(i):
    return {"id": i.id, "title": i.title, "description": i.description, "service": i.service, "severity": i.severity,
            "status": i.status, "error_message": i.error_message, "logs": i.logs or [], "metrics": i.metrics or [],
            "events": i.events or [], "is_demo": bool(i.is_demo), "resolution_notes": i.resolution_notes,
            "created_at": i.created_at.strftime(F), "resolved_at": i.resolved_at.strftime(F) if i.resolved_at else None}

def _get(db, iid):
    i = db.get(Incident, iid)
    if not i:
        raise HTTPException(404, f"Incident {iid} not found")
    return i

def _run(db, i):
    d = _inc(i)
    res = rca.analyze(d)
    exp, src = ai.explain(d, res)
    a = Analysis(incident_id=i.id, result=res, explanation=exp, explanation_source=src)
    db.add(a); db.commit(); db.refresh(a)
    return a

def _an(a):
    return None if not a else {"id": a.id, "result": a.result, "explanation": a.explanation,
                               "explanation_source": a.explanation_source, "created_at": a.created_at.strftime(F)}

@router.get("/health")
def health():
    return {"status": "ok", "gemini_configured": bool(os.getenv("GEMINI_API_KEY", "").strip())}

@router.post("/incidents", status_code=201)
def create_incident(body: IncidentCreate, db: Session = Depends(get_db)):
    i = Incident(**body.model_dump()); db.add(i); db.commit(); db.refresh(i)
    return _inc(i)

@router.get("/incidents")
def list_incidents(severity: str | None = None, service: str | None = None, status: str | None = None,
                   q: str | None = None, db: Session = Depends(get_db)):
    qs = db.query(Incident)
    if severity: qs = qs.filter(Incident.severity == severity)
    if service: qs = qs.filter(Incident.service == service)
    if status: qs = qs.filter(Incident.status == status)
    if q: qs = qs.filter(or_(Incident.description.ilike(f"%{q}%"), Incident.title.ilike(f"%{q}%")))
    out = []
    for i in qs.order_by(Incident.id.desc()).all():
        d = _inc(i); d.pop("logs"); d.pop("metrics"); out.append(d)
    return out

@router.get("/incidents/{iid}")
def detail(iid: int, db: Session = Depends(get_db)):
    i = _get(db, iid)
    return {**_inc(i), "latest_analysis": _an(i.analyses[0] if i.analyses else None), "analysis_count": len(i.analyses)}

@router.post("/incidents/{iid}/analyze")
def analyze(iid: int, db: Session = Depends(get_db)):
    return _an(_run(db, _get(db, iid)))

@router.get("/incidents/{iid}/analyses")
def history(iid: int, db: Session = Depends(get_db)):
    return [_an(a) for a in _get(db, iid).analyses]

@router.post("/incidents/{iid}/logs")
async def upload_logs(iid: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    i = _get(db, iid)
    try:
        parsed = logsvc.parse_logs(file.filename, await file.read())
    except logsvc.LogParseError as e:
        raise HTTPException(400, str(e))
    i.logs = (i.logs or []) + parsed; db.commit()
    return {"added": len(parsed), "summary": logsvc.summarize_logs(i.logs)}

@router.post("/incidents/{iid}/metrics")
def add_metrics(iid: int, body: MetricsIn, db: Session = Depends(get_db)):
    i = _get(db, iid)
    i.metrics = (i.metrics or []) + body.metrics; db.commit()
    return {"total_points": len(i.metrics)}

@router.get("/incidents/{iid}/anomalies")
def anomalies(iid: int, db: Session = Depends(get_db)):
    return detect_anomalies(_get(db, iid).metrics or [])

@router.post("/incidents/{iid}/resolve")
def resolve(iid: int, body: ResolveIn, db: Session = Depends(get_db)):
    i = _get(db, iid)
    i.status, i.resolution_notes, i.resolved_at = "resolved", body.notes, datetime.utcnow(); db.commit()
    return _inc(i)

@router.get("/scenarios")
def list_scenarios():
    return scenarios.info()

@router.post("/scenarios/{key}", status_code=201)
def load_scenario(key: str, db: Session = Depends(get_db)):
    if key not in scenarios.SCENARIOS:
        raise HTTPException(404, "Unknown scenario")
    i = Incident(**scenarios.build(key), is_demo=1); db.add(i); db.commit(); db.refresh(i)
    _run(db, i)
    return _inc(i)

@router.get("/live/tick")
def tick(t: int = Query(ge=0), failing_since: int | None = None):
    return scenarios.live_tick(t, failing_since)

@router.post("/live/incident", status_code=201)
def live_incident(body: LivePoint, db: Session = Depends(get_db)):
    buf = body.buffer
    if len(buf) < 10:
        raise HTTPException(400, "Need at least 10 buffered points")
    last, keys = buf[-1], ("ts", "cpu", "memory", "latency", "error_rate", "db_conn")
    logs = [{"ts": last["ts"], "service": "postgres-db", "level": "WARN", "message": "Connection pool usage high"}] if last.get("db_conn", 0) >= 90 else []
    i = Incident(title="[DEMO DATA] Threshold breach: " + ", ".join(last.get("breaches") or ["metric"]), service=body.service,
                 severity="critical", description="Simulated metrics crossed a threshold (not real production data).",
                 error_message="Threshold breach in simulated monitoring", is_demo=1, logs=logs, events=[],
                 metrics=[{k: p.get(k) for k in keys} for p in buf])
    db.add(i); db.commit(); db.refresh(i); _run(db, i)
    return _inc(i)

@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    all_ = db.query(Incident).all()
    res = [i for i in all_ if i.status == "resolved"]
    mttr = [(i.resolved_at - i.created_at).total_seconds() / 60 for i in res if i.resolved_at]
    tops, trend, svc = {}, {}, {}
    for i in all_:
        d = i.created_at.strftime("%Y-%m-%d"); trend[d] = trend.get(d, 0) + 1
        if i.analyses and i.analyses[0].result.get("top_cause"):
            c = i.analyses[0].result["top_cause"]; tops[c] = tops.get(c, 0) + 1
        svc[i.service] = svc.get(i.service, 0) + (1 if i.status == "active" else 0)
    return {"total": len(all_), "active": len(all_) - len(res), "resolved": len(res),
            "critical": sum(1 for i in all_ if i.severity == "critical"),
            "avg_time_to_resolve_min": round(sum(mttr) / len(mttr), 1) if mttr else None,
            "estimated_downtime_min": round(sum(mttr), 1),
            "severity": {s: sum(1 for i in all_ if i.severity == s) for s in ("critical", "warning", "info")},
            "trend": [{"date": k, "incidents": v} for k, v in sorted(trend.items())],
            "top_causes": [{"cause": k, "count": v} for k, v in sorted(tops.items(), key=lambda x: -x[1])[:5]],
            "service_health": [{"service": k, "active_incidents": v, "status": "degraded" if v else "healthy"} for k, v in svc.items()]}

@router.get("/incidents/{iid}/report")
def report(iid: int, format: str = Query("json", pattern="^(json|csv)$"), db: Session = Depends(get_db)):
    i = _get(db, iid)
    a = _an(i.analyses[0]) if i.analyses else None
    doc = {"incident": _inc(i), "analysis": a, "disclaimer": "Suspected causes only. Human review required before any action."}
    if format == "json":
        return Response(json.dumps(doc, indent=2), media_type="application/json",
                        headers={"Content-Disposition": f"attachment; filename=incident-{iid}.json"})
    buf = io.StringIO(); w = csv.writer(buf); w.writerow(["section", "field", "value"])
    for k in ("id", "title", "service", "severity", "status", "error_message", "resolution_notes"):
        w.writerow(["summary", k, doc["incident"][k]])
    if a:
        for t in a["result"]["timeline"]: w.writerow(["timeline", t["ts"], f"[{t['kind']}] {t['text']}"])
        for c in a["result"]["candidates"]:
            w.writerow(["candidate", c["cause"], c["confidence"]])
            for e in c["supporting_evidence"]: w.writerow(["evidence", c["cause"], e])
        for c in a["result"]["checklist"]: w.writerow(["checklist", c["group"], c["item"]])
        for k, v in (a["explanation"] or {}).items(): w.writerow(["ai_explanation", k, json.dumps(v)])
    for l in i.logs or []: w.writerow(["log", l["ts"], f"{l['level']} {l['service']}: {l['message']}"])
    for m in i.metrics or []: w.writerow(["metric", m.get("ts"), json.dumps(m)])
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=incident-{iid}.csv"})
