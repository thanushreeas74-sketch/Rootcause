import { useEffect, useRef, useState, useCallback } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell, CartesianGrid } from 'recharts'
import { Activity, AlertTriangle, CheckCircle2, Clock, Download, FileUp, History, LayoutDashboard, Play, RefreshCw, Radio, Siren, Search } from 'lucide-react'
import { api } from './api'

const SEV = { critical: 'bg-red-500/20 text-red-300', warning: 'bg-amber-500/20 text-amber-300', info: 'bg-cyan-500/20 text-cyan-300' }
const Badge = ({ s }) => <span className={`px-2 py-0.5 rounded text-xs ${SEV[s] || ''}`}>{s}</span>
const Status = ({ s }) => <span className={`px-2 py-0.5 rounded text-xs ${s === 'resolved' ? 'bg-green-500/20 text-green-300' : 'bg-red-500/20 text-red-300'}`}>{s}</span>
const tip = { contentStyle: { background: '#111d38', border: '1px solid #1a2b50' } }
const Err = ({ e }) => e ? <div className="card border-red-500/50 text-red-300 text-sm">{e}</div> : null
const Stat = ({ icon: I, label, value, c = 'text-cyan-400' }) => (
  <div className="card"><I className={`w-5 h-5 ${c}`} /><div className="text-2xl font-semibold mt-2">{value ?? '—'}</div><div className="text-xs text-slate-400">{label}</div></div>)

function Dashboard({ open, go }) {
  const [s, setS] = useState(null), [list, setList] = useState([]), [e, setE] = useState('')
  useEffect(() => { api.get('/stats').then(setS).catch(x => setE(x.message)); api.get('/incidents').then(setList).catch(() => {}) }, [])
  if (e) return <Err e={e} />
  if (!s) return <p className="text-slate-400">Loading…</p>
  const sev = Object.entries(s.severity).map(([name, value]) => ({ name, value }))
  const col = { critical: '#ef4444', warning: '#f59e0b', info: '#22d3ee' }
  return (<div className="space-y-4">
    <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
      <Stat icon={Siren} label="Total incidents" value={s.total} /><Stat icon={Activity} label="Active" value={s.active} c="text-amber-400" />
      <Stat icon={CheckCircle2} label="Resolved" value={s.resolved} c="text-green-400" /><Stat icon={AlertTriangle} label="Critical" value={s.critical} c="text-red-400" />
      <Stat icon={Clock} label="Avg time to resolve (min)" value={s.avg_time_to_resolve_min} /><Stat icon={Clock} label="Estimated downtime (min)" value={s.estimated_downtime_min} c="text-red-400" /></div>
    {s.total === 0 && <div className="card">No incidents yet. <button className="btn ml-2" onClick={() => go('detect')}>Load a demo scenario</button></div>}
    <div className="grid lg:grid-cols-3 gap-3">
      <div className="card"><h3 className="mb-2 text-sm text-slate-300">Incident trend</h3><ResponsiveContainer height={180}><LineChart data={s.trend}><CartesianGrid stroke="#1a2b50" /><XAxis dataKey="date" stroke="#64748b" fontSize={11} /><YAxis allowDecimals={false} stroke="#64748b" fontSize={11} /><Tooltip {...tip} /><Line dataKey="incidents" stroke="#22d3ee" /></LineChart></ResponsiveContainer></div>
      <div className="card"><h3 className="mb-2 text-sm text-slate-300">Severity</h3><ResponsiveContainer height={180}><PieChart><Pie data={sev} dataKey="value" nameKey="name" outerRadius={70} label>{sev.map(x => <Cell key={x.name} fill={col[x.name]} />)}</Pie><Tooltip {...tip} /></PieChart></ResponsiveContainer></div>
      <div className="card"><h3 className="mb-2 text-sm text-slate-300">Service health</h3>{s.service_health.length === 0 && <p className="text-xs text-slate-500">No data</p>}
        {s.service_health.map(x => <div key={x.service} className="flex justify-between text-sm py-1"><span>{x.service}</span><span className={x.status === 'healthy' ? 'text-green-400' : 'text-amber-400'}>{x.status} ({x.active_incidents})</span></div>)}</div></div>
    <div className="grid lg:grid-cols-3 gap-3">
      <div className="card lg:col-span-2"><h3 className="mb-2 text-sm text-slate-300">Recent incidents</h3>
        <table className="w-full text-sm"><tbody>{list.slice(0, 6).map(i => <tr key={i.id} className="border-t border-navy-700 cursor-pointer hover:bg-navy-700" onClick={() => open(i.id)}>
          <td className="py-1.5">#{i.id} {i.title}{i.is_demo && <span className="ml-2 text-xs text-cyan-300">DEMO</span>}</td><td><Badge s={i.severity} /></td><td><Status s={i.status} /></td></tr>)}</tbody></table></div>
      <div className="card"><h3 className="mb-2 text-sm text-slate-300">Top suspected root causes</h3>{s.top_causes.map(c => <div key={c.cause} className="flex justify-between text-sm py-1"><span>{c.cause}</span><b>{c.count}</b></div>)}
        <div className="mt-3 flex gap-2 flex-wrap"><button className="btn" onClick={() => go('detect')}>New / demo incident</button><button className="btn2" onClick={() => go('live')}>Live demo</button></div></div></div></div>)
}

function Detect({ open }) {
  const [sc, setSc] = useState([]), [e, setE] = useState(''), [busy, setBusy] = useState(false)
  const [f, setF] = useState({ title: '', service: '', severity: 'warning', description: '', error_message: '' })
  const [file, setFile] = useState(null), [iid, setIid] = useState(''), [msg, setMsg] = useState('')
  useEffect(() => { api.get('/scenarios').then(setSc).catch(x => setE(x.message)) }, [])
  const run = async (fn) => { setE(''); setMsg(''); setBusy(true); try { await fn() } catch (x) { setE(x.message) } setBusy(false) }
  return (<div className="space-y-4"><Err e={e} />{msg && <div className="card text-green-300 text-sm">{msg}</div>}
    <div className="card"><h3 className="mb-2 font-semibold">Demo scenarios <span className="text-xs text-cyan-300">(DEMO DATA, deterministic)</span></h3>
      <div className="grid md:grid-cols-3 gap-3">{sc.map(s => <div key={s.key} className="card bg-navy-900"><div className="font-medium text-sm">{s.title}</div>
        <p className="text-xs text-slate-400 my-2">{s.initial_condition}<br />Expected: {s.expected_anomaly}</p>
        <button className="btn" disabled={busy} onClick={() => run(async () => open((await api.post('/scenarios/' + s.key)).id))}><Play className="inline w-3 h-3 mr-1" />Run demo</button></div>)}</div></div>
    <div className="grid md:grid-cols-2 gap-3">
      <div className="card space-y-2"><h3 className="font-semibold">Create incident</h3>
        <input className="inp" placeholder="Title" value={f.title} onChange={x => setF({ ...f, title: x.target.value })} />
        <input className="inp" placeholder="Service (e.g. api-gateway)" value={f.service} onChange={x => setF({ ...f, service: x.target.value })} />
        <select className="inp" value={f.severity} onChange={x => setF({ ...f, severity: x.target.value })}><option>critical</option><option>warning</option><option>info</option></select>
        <textarea className="inp" placeholder="Description" value={f.description} onChange={x => setF({ ...f, description: x.target.value })} />
        <input className="inp" placeholder="Error message" value={f.error_message} onChange={x => setF({ ...f, error_message: x.target.value })} />
        <button className="btn" disabled={busy} onClick={() => run(async () => open((await api.post('/incidents', f)).id))}>Create incident</button></div>
      <div className="card space-y-2"><h3 className="font-semibold">Upload logs (CSV / JSON)</h3>
        <p className="text-xs text-slate-400">Columns: timestamp, service, level, message. Attach to an existing incident ID.</p>
        <input className="inp" placeholder="Incident ID" value={iid} onChange={x => setIid(x.target.value)} />
        <input type="file" accept=".csv,.json" className="text-sm" onChange={x => setFile(x.target.files[0])} />
        <button className="btn" disabled={busy || !file || !iid} onClick={() => run(async () => { const r = await api.upload(`/incidents/${iid}/logs`, file); setMsg(`Added ${r.added} log lines to incident ${iid}. Open it and re-run analysis.`) })}><FileUp className="inline w-3 h-3 mr-1" />Upload</button>
        <p className="text-xs text-slate-400 pt-2">Metrics: POST /api/incidents/{'{id}'}/metrics (see API docs at :8000/docs).</p></div></div></div>)
}

function Detail({ id, back }) {
  const [d, setD] = useState(null), [e, setE] = useState(''), [notes, setNotes] = useState(''), [busy, setBusy] = useState(false)
  const load = useCallback(() => api.get('/incidents/' + id).then(setD).catch(x => setE(x.message)), [id])
  useEffect(() => { load() }, [load])
  if (e) return <Err e={e} />
  if (!d) return <p className="text-slate-400">Loading…</p>
  const a = d.latest_analysis, r = a?.result, ex = a?.explanation
  const act = async (fn) => { setBusy(true); setE(''); try { await fn(); await load() } catch (x) { setE(x.message) } setBusy(false) }
  const m = d.metrics.map(x => ({ ...x, t: x.ts.slice(11, 16) }))
  const chart = (title, keys, colors) => <div className="card"><h4 className="text-sm text-slate-300 mb-1">{title}</h4><ResponsiveContainer height={150}><LineChart data={m}><CartesianGrid stroke="#1a2b50" /><XAxis dataKey="t" stroke="#64748b" fontSize={10} /><YAxis stroke="#64748b" fontSize={10} /><Tooltip {...tip} />{keys.map((k, i) => <Line key={k} dot={false} dataKey={k} stroke={colors[i]} />)}</LineChart></ResponsiveContainer></div>
  return (<div className="space-y-4"><button className="btn2" onClick={back}>← Back</button>
    <div className="card"><div className="flex flex-wrap gap-2 items-center"><h2 className="text-lg font-semibold">#{d.id} {d.title}</h2><Badge s={d.severity} /><Status s={d.status} />{d.is_demo && <span className="text-xs text-cyan-300">DEMO DATA</span>}</div>
      <p className="text-sm text-slate-300 mt-1">{d.service} — {d.description}</p>{d.error_message && <p className="text-xs text-red-300 mt-1 font-mono">{d.error_message}</p>}
      <div className="flex gap-2 mt-3 flex-wrap"><button className="btn" disabled={busy} onClick={() => act(() => api.post(`/incidents/${id}/analyze`))}><RefreshCw className="inline w-3 h-3 mr-1" />{a ? 'Re-run analysis' : 'Run analysis'}</button>
        <a className="btn2" href={`/api/incidents/${id}/report?format=json`}><Download className="inline w-3 h-3 mr-1" />JSON</a><a className="btn2" href={`/api/incidents/${id}/report?format=csv`}><Download className="inline w-3 h-3 mr-1" />CSV</a></div></div>
    {m.length > 0 && <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-3">{chart('CPU & memory (%)', ['cpu', 'memory'], ['#22d3ee', '#a78bfa'])}{chart('Response time (ms)', ['latency'], ['#f59e0b'])}{chart('DB connection use (%)', ['db_conn'], ['#ef4444'])}{chart('Error rate (%)', ['error_rate'], ['#f87171'])}</div>}
    {r && <>
      <div className={`card ${r.top_cause ? '' : 'border-amber-500/60'}`}><h3 className="font-semibold">{r.verdict}</h3><p className="text-xs text-slate-400">{r.disclaimer}</p>
        {r.log_summary.error_frequency.length > 0 && <ResponsiveContainer height={120}><BarChart data={r.log_summary.error_frequency}><XAxis dataKey="minute" tickFormatter={v => v.slice(11)} stroke="#64748b" fontSize={10} /><YAxis allowDecimals={false} stroke="#64748b" fontSize={10} /><Tooltip {...tip} /><Bar dataKey="errors" fill="#ef4444" /></BarChart></ResponsiveContainer>}</div>
      <div className="grid lg:grid-cols-2 gap-3"><div className="space-y-3">{r.candidates.map((c, i) => <div key={c.cause} className="card"><div className="flex justify-between"><b>{i + 1}. {c.cause}</b><span className="text-cyan-300 text-sm">strength {Math.round(c.confidence * 100)}%</span></div>
        <p className="text-xs text-amber-300">{c.label}</p><div className="h-1.5 bg-navy-900 rounded my-2"><div className="h-1.5 bg-cyan-400 rounded" style={{ width: c.confidence * 100 + '%' }} /></div>
        <p className="text-xs text-slate-400">Impact: {c.impact} Affected: {c.affected_services.join(', ')}</p>
        <ul className="text-sm list-disc ml-5 mt-1 text-green-300">{c.supporting_evidence.map(x => <li key={x}>{x}</li>)}</ul>
        <ul className="text-sm list-disc ml-5 text-slate-400">{c.contradicting_evidence.map(x => <li key={x}>{x}</li>)}</ul>
        {c.missing_evidence.length > 0 && <p className="text-xs text-amber-300 mt-1">Missing evidence: {c.missing_evidence.join('; ')}</p>}</div>)}</div>
        <div className="space-y-3"><div className="card"><h3 className="font-semibold mb-2">Timeline</h3>{r.timeline.map((t, i) => <div key={i} className={`text-sm py-1 border-l-2 pl-3 ${t.earliest ? 'border-red-400 bg-red-500/10' : t.kind === 'inferred' ? 'border-dashed border-slate-500 text-slate-400' : 'border-cyan-500'}`}>
          <span className="text-xs text-slate-400">{t.ts.replace('T', ' ').replace('Z', '')} · {t.kind}{t.earliest ? ' · earliest anomaly' : ''}</span><br />{t.text}</div>)}</div>
          {ex && <div className="card"><h3 className="font-semibold mb-1">Explanation <span className="text-xs text-cyan-300">({a.explanation_source === 'gemini' ? 'Gemini' : 'local rule-based'})</span></h3>
            {Object.entries(ex).map(([k, v]) => <p key={k} className="text-sm mb-1"><b className="text-slate-300">{k.replaceAll('_', ' ')}: </b>{Array.isArray(v) ? v.join('; ') : String(v)}</p>)}</div>}</div></div>
      <div className="card"><h3 className="font-semibold mb-1">Preventive checklist <span className="text-xs text-amber-300">(human review required — nothing is executed automatically)</span></h3>
        {r.checklist.map((c, i) => <label key={i} className="flex gap-2 text-sm py-1 items-start"><input type="checkbox" className="mt-1" /><span><b>{c.group}:</b> {c.item}<br /><span className="text-xs text-slate-400">Why: {c.reason}{c.evidence.length ? ' · Evidence: ' + c.evidence.join('; ') : ''}</span></span></label>)}</div></>}
    <div className="card"><h3 className="font-semibold mb-1">Resolution</h3>{d.status === 'resolved' ? <p className="text-sm text-green-300">Resolved: {d.resolution_notes}</p> :
      <div className="flex gap-2"><input className="inp" placeholder="Resolution notes" value={notes} onChange={x => setNotes(x.target.value)} /><button className="btn" disabled={busy || !notes} onClick={() => act(() => api.post(`/incidents/${id}/resolve`, { notes }))}>Mark resolved</button></div>}</div></div>)
}

function HistoryPage({ open }) {
  const [list, setList] = useState([]), [e, setE] = useState(''), [fl, setFl] = useState({ q: '', severity: '', status: '', service: '' })
  useEffect(() => { const p = new URLSearchParams(Object.entries(fl).filter(([, v]) => v)); api.get('/incidents?' + p).then(setList).catch(x => setE(x.message)) }, [fl])
  return (<div className="space-y-3"><Err e={e} /><div className="grid grid-cols-2 md:grid-cols-4 gap-2">
    <div className="relative"><Search className="w-4 h-4 absolute left-2 top-2 text-slate-400" /><input className="inp pl-8" placeholder="Search" value={fl.q} onChange={x => setFl({ ...fl, q: x.target.value })} /></div>
    <select className="inp" onChange={x => setFl({ ...fl, severity: x.target.value })}><option value="">All severities</option><option>critical</option><option>warning</option><option>info</option></select>
    <select className="inp" onChange={x => setFl({ ...fl, status: x.target.value })}><option value="">All statuses</option><option>active</option><option>resolved</option></select>
    <input className="inp" placeholder="Service" value={fl.service} onChange={x => setFl({ ...fl, service: x.target.value })} /></div>
    <div className="card"><table className="w-full text-sm"><tbody>{list.map(i => <tr key={i.id} className="border-t border-navy-700 cursor-pointer hover:bg-navy-700" onClick={() => open(i.id)}><td className="py-1.5">#{i.id} {i.title}</td><td>{i.service}</td><td><Badge s={i.severity} /></td><td><Status s={i.status} /></td></tr>)}</tbody></table>
      {list.length === 0 && <p className="text-sm text-slate-400">No incidents match.</p>}</div></div>)
}

const LIM = { cpu: 85, memory: 85, latency: 1000, error_rate: 5, db_conn: 90 }
function Live({ open }) {
  const [buf, setBuf] = useState([]), [on, setOn] = useState(false), [fail, setFail] = useState(null), [e, setE] = useState(''), t = useRef(0), made = useRef(false)
  useEffect(() => {
    if (!on) return
    const id = setInterval(async () => {
      try {
        const p = await api.get(`/live/tick?t=${t.current++}${fail !== null ? '&failing_since=' + fail : ''}`)
        setBuf(b => [...b, p].slice(-40))
        if (p.breaches.length && !made.current && t.current > 12) {
          made.current = true
          const b = [...buf, p].slice(-40); const inc = await api.post('/live/incident', { buffer: b }); open(inc.id)
        }
      } catch (x) { setE(x.message) }
    }, 2000)
    return () => clearInterval(id)
  }, [on, fail, buf, open])
  const last = buf[buf.length - 1]
  return (<div className="space-y-3"><div className="card flex flex-wrap gap-2 items-center"><Radio className="w-4 h-4 text-amber-400" /><b className="text-amber-300">DEMO DATA — simulated metrics, not real production monitoring</b>
    <button className="btn" onClick={() => { setOn(!on) }}>{on ? 'Pause' : 'Start'}</button>
    <button className="btn2" disabled={!on || fail !== null} onClick={() => { setFail(t.current); made.current = false }}>Simulate DB failure</button>
    <button className="btn2" onClick={() => { setBuf([]); setFail(null); t.current = 0; made.current = false }}>Reset</button></div><Err e={e} />
    {last && <div className="grid grid-cols-2 md:grid-cols-5 gap-3">{Object.keys(LIM).map(k => <div key={k} className={`card ${last[k] >= LIM[k] ? 'border-red-500' : ''}`}><div className="text-xs text-slate-400">{k} (limit {LIM[k]})</div><div className={`text-xl ${last[k] >= LIM[k] ? 'text-red-400' : ''}`}>{last[k]}</div></div>)}</div>}
    {buf.length > 0 && <div className="card"><ResponsiveContainer height={220}><LineChart data={buf}><CartesianGrid stroke="#1a2b50" /><XAxis dataKey="t" stroke="#64748b" /><YAxis stroke="#64748b" /><Tooltip {...tip} />
      <Line dot={false} dataKey="cpu" stroke="#22d3ee" /><Line dot={false} dataKey="memory" stroke="#a78bfa" /><Line dot={false} dataKey="db_conn" stroke="#ef4444" /><Line dot={false} dataKey="error_rate" stroke="#f59e0b" /></LineChart></ResponsiveContainer></div>}
    <p className="text-xs text-slate-400">After a threshold breach (with at least 12 points buffered), an incident is created and analyzed automatically.</p></div>)
}

export default function App() {
  const [tab, setTab] = useState('dash'), [sel, setSel] = useState(null)
  const open = useCallback((id) => { setSel(id); setTab('detail') }, [])
  const nav = [['dash', 'Overview', LayoutDashboard], ['detect', 'Detect', Siren], ['history', 'History', History], ['live', 'Live demo', Radio]]
  return (<div className="min-h-screen bg-navy-950"><header className="bg-navy-900 border-b border-navy-700 px-4 py-3 flex flex-wrap items-center gap-4">
    <div><div className="text-lg font-bold text-cyan-400">RootCause AI</div><div className="text-xs text-slate-400">Don't just detect failures. Understand why they happen.</div></div>
    <nav className="flex gap-1 flex-wrap">{nav.map(([k, l, I]) => <button key={k} onClick={() => setTab(k)} className={`px-3 py-1.5 rounded-md text-sm flex items-center gap-1 ${tab === k ? 'bg-cyan-500/20 text-cyan-300' : 'hover:bg-navy-700'}`}><I className="w-4 h-4" />{l}</button>)}</nav></header>
    <main className="p-4 max-w-7xl mx-auto">{tab === 'dash' && <Dashboard open={open} go={setTab} />}{tab === 'detect' && <Detect open={open} />}{tab === 'history' && <HistoryPage open={open} />}
      {tab === 'live' && <Live open={open} />}{tab === 'detail' && <Detail id={sel} back={() => setTab('history')} />}</main></div>)
}
