# RootCause AI
*Don't just detect failures. Understand why they happen.*
AI-assisted incident root cause analysis: FastAPI + SQLite + scikit-learn (Isolation Forest) + rule-based ranking + optional Gemini + React dashboard.
Findings are **suspected causes** (correlation, not proof). Nothing is ever executed automatically.

## Windows setup (needs Python 3.10+ and Node 18+)
**Terminal 1 – backend (VS Code: Terminal > New Terminal)**
```
cd rootcause-ai\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy ..\.env.example .env
uvicorn app.main:app --reload --port 8000
```
API docs: http://127.0.0.1:8000/docs

**Terminal 2 – frontend**
```
cd rootcause-ai\frontend
npm install
npm run dev
```
Open http://localhost:5173

If PowerShell blocks activation: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## Gemini key (optional)
Get a key at https://aistudio.google.com, put `GEMINI_API_KEY=...` in `backend\.env` (never in frontend code, never committed). Restart uvicorn. Without a key, the local rule-based explainer is used (shown as "local rule-based" in the UI). Gemini failures also fall back automatically.

## Tests
```
cd backend
pytest -q
```

## Demo (no key needed)
Detect tab > Run demo (DB pool / memory leak / bad config). Deterministic: same input, same ranking. Live demo tab > Start > Simulate DB failure (labelled DEMO DATA).

## GitHub
```
cd rootcause-ai
git init
git add .
git commit -m "RootCause AI"
git branch -M main
git remote add origin https://github.com/YOU/rootcause-ai.git
git push -u origin main
```
`.env` is git-ignored; check `git status` shows no secrets first.

## Deploy (outline)
Backend: Render/Railway, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, set `GEMINI_API_KEY` and `CORS_ORIGINS` as env vars. Frontend: Vercel/Netlify, `npm run build`, and point `/api` at the backend (replace the Vite proxy with a rewrite or a `VITE_API` base URL). SQLite resets on ephemeral hosts; use a volume or Postgres for persistence.

## Verification checklist
- [ ] `/api/health` returns ok; `/docs` loads
- [ ] 3 demos run and rank: DB pool, Memory leak, Config change
- [ ] Create incident; upload `sample_data/sample_logs.csv` (and a bad .txt shows an error)
- [ ] Re-run analysis; filter/search History; Mark resolved with notes
- [ ] JSON and CSV reports download
- [ ] Empty incident shows "Root cause not confirmed. More evidence is required."
- [ ] Live demo breach creates an incident
- [ ] `pytest -q` passes

## Scope notes
Implemented: all 10 modules in compact form. Not implemented: the extra sample scenarios (API timeout, CPU overload, network latency) as ready-made demos (the rules exist), a dedicated metrics-upload form (API only), and auth.
