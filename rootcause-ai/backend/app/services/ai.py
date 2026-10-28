"""Explanation service: Gemini via backend, validated JSON, local fallback."""
import json, os
from .rca import NOT_CONFIRMED

KEYS = ["what_happened", "when_began", "affected_services", "most_likely_cause", "supporting_evidence",
        "other_explanations", "investigate_next", "prevention"]

def local_explanation(inc: dict, res: dict) -> dict:
    top = res["candidates"][0] if res["candidates"] else None
    return {"what_happened": f"{inc['title']} on {inc['service']}. {inc.get('error_message') or ''}".strip(),
            "when_began": res["timeline"][0]["ts"] if res["timeline"] else "Unknown",
            "affected_services": res["affected_services"],
            "most_likely_cause": f"Suspected: {top['cause']} (evidence strength {top['confidence']})" if top else NOT_CONFIRMED,
            "supporting_evidence": top["supporting_evidence"] if top else [],
            "other_explanations": res["alternatives"],
            "investigate_next": top["recommended_investigation"] if top else ["Collect more logs and metrics"],
            "prevention": top["preventive_action"] if top else []}

def explain(inc: dict, res: dict) -> tuple[dict, str]:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return local_explanation(inc, res), "local"
    try:
        from google import genai
        payload = {"incident": {k: inc.get(k) for k in ("title", "service", "error_message", "events")},
                   "analysis": {k: res[k] for k in ("verdict", "candidates", "timeline", "affected_services")},
                   "log_sample": (inc.get("logs") or [])[:40]}
        prompt = (f"You are an incident analyst. Using ONLY the data below, answer as JSON with exactly these keys: {KEYS}. "
                  "Never invent logs, metrics, timestamps or deployments. Call causes 'suspected'; correlation is not proof. "
                  f"If evidence is insufficient say: '{NOT_CONFIRMED}'.\nDATA:\n{json.dumps(payload)[:30000]}")
        r = genai.Client(api_key=key).models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), contents=prompt,
            config={"response_mime_type": "application/json"})
        data = json.loads(r.text)
        if isinstance(data, dict) and all(k in data for k in KEYS):
            return data, "gemini"
    except Exception as e:
        print("Gemini unavailable, using local fallback:", type(e).__name__)
    return local_explanation(inc, res), "local"
