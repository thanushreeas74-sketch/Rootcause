import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["GEMINI_API_KEY"] = ""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import scenarios, rca, logs as L
from app.services.anomaly import detect_anomalies

client = TestClient(app)

def analyze(key):
    return rca.analyze(scenarios.build(key))

def test_db_pool_ranked_first_and_deterministic():
    a, b = analyze("db_pool"), analyze("db_pool")
    assert a["top_cause"] == "Database connection pool exhaustion"
    assert a["candidates"] == b["candidates"]

def test_memory_leak():
    assert analyze("memory_leak")["top_cause"] == "Memory leak"

def test_bad_config():
    assert analyze("bad_config")["top_cause"] == "Incorrect deployment / configuration change"

def test_anomaly_order():
    an = detect_anomalies(scenarios.build("db_pool")["metrics"])
    assert an["order"][0] == "db_conn"

def test_insufficient_evidence():
    r = rca.analyze({"title": "x", "service": "s", "logs": [], "metrics": [], "events": []})
    assert r["verdict"] == rca.NOT_CONFIRMED and r["candidates"] == []

def test_log_parsing_csv():
    data = b"timestamp,service,level,message\n2025-01-01T10:00:00Z,api,error,boom 5\n"
    assert L.parse_logs("a.csv", data)[0]["level"] == "ERROR"

@pytest.mark.parametrize("name,data", [("a.txt", b"x"), ("a.csv", b""), ("a.csv", b"foo,bar\n1,2\n"), ("a.json", b"{bad")])
def test_invalid_uploads(name, data):
    with pytest.raises(L.LogParseError):
        L.parse_logs(name, data)

def test_incident_lifecycle_api():
    r = client.post("/api/incidents", json={"title": "Test incident", "service": "api"})
    assert r.status_code == 201
    iid = r.json()["id"]
    assert client.post(f"/api/incidents/{iid}/analyze").status_code == 200
    assert client.post(f"/api/incidents/{iid}/resolve", json={"notes": "fixed"}).json()["status"] == "resolved"
    assert client.get(f"/api/incidents/{iid}/report?format=csv").status_code == 200

def test_api_errors():
    assert client.get("/api/incidents/99999").status_code == 404
    assert client.post("/api/incidents", json={"title": "x"}).status_code == 422
    bad = client.post("/api/incidents/1/logs", files={"file": ("a.txt", b"hi")})
    assert bad.status_code == 400

def test_scenario_and_stats():
    assert client.post("/api/scenarios/db_pool").status_code == 201
    assert client.get("/api/stats").json()["total"] >= 1
