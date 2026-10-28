async function req(path, opts = {}) {
  const r = await fetch('/api' + path, opts)
  if (!r.ok) {
    let m = r.statusText
    try { const j = await r.json(); m = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail) } catch {}
    throw new Error(m)
  }
  return r
}
const json = (method, body) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export const api = {
  get: async (p) => (await req(p)).json(),
  post: async (p, b) => (await req(p, json('POST', b ?? {}))).json(),
  upload: async (p, file) => { const f = new FormData(); f.append('file', file); return (await req(p, { method: 'POST', body: f })).json() },
}
