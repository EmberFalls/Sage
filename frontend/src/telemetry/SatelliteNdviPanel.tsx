import React, { useState } from 'react'
import { RefreshCw, Satellite } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'

const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const dateValue = (offset: number) => { const d = new Date(); d.setDate(d.getDate() + offset); return d.toISOString().slice(0, 10) }

export function SatelliteNdviPanel({ district = 'your plot', asOf: _asOf }: { district?: string; crop?: string; stage?: string; asOf?: string }) {
  const { token } = useAuth()
  const [bbox, setBbox] = useState('')
  const [start, setStart] = useState(dateValue(-14))
  const [end, setEnd] = useState(dateValue(0))
  const [cloudLimit, setCloudLimit] = useState('80')
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const load = async (event: React.FormEvent) => {
    event.preventDefault(); setLoading(true); setError(''); setData(null)
    const coords = bbox.split(',').map(value => Number(value.trim()))
    if (coords.length !== 4 || coords.some(value => !Number.isFinite(value))) {
      setError('Enter plot bounds as west, south, east, north coordinates.'); setLoading(false); return
    }
    try {
      const response = await fetch(`${API}/api/telemetry/ndvi`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ bbox: coords, start_date: start, end_date: end, max_scene_cloud_pct: Number(cloudLimit) }),
      })
      const body = await response.json()
      if (!response.ok) throw new Error(body.detail || 'Satellite data request failed')
      setData(body)
    } catch (err: any) { setError(err.message || 'Satellite data request failed') }
    finally { setLoading(false) }
  }
  const active = data?.status === 'live_observation'
  return <section className="card telemetry-card" aria-labelledby="ndvi-title">
    <div className="section-title"><div><h2 id="ndvi-title"><Satellite size={17} /> Sentinel-2 vegetation index</h2>
      <p>NDVI area average for a small plot box near {district}. Public satellite imagery; no boundary is saved.</p></div></div>
    <form onSubmit={load}>
      <label className="control-label"><span>Plot bounds (west, south, east, north; WGS84)</span><input value={bbox} onChange={e => setBbox(e.target.value)} placeholder="73.8500, 18.5200, 73.8550, 18.5250" aria-describedby="bbox-help" /></label>
      <small id="bbox-help" className="microcopy">Use a plot-only rectangle; max 0.02° per side. Bounds are sent to Sage and Copernicus Data Space to calculate this request; they are not saved by Sage.</small>
      <div className="toolbar" style={{ alignItems: 'end', flexWrap: 'wrap' }}>
        <label className="control-label"><span>From</span><input type="date" value={start} max={end} onChange={e => setStart(e.target.value)} /></label>
        <label className="control-label"><span>Through</span><input type="date" value={end} min={start} max={dateValue(0)} onChange={e => setEnd(e.target.value)} /></label>
        <label className="control-label"><span>Max scene cloud %</span><input type="number" min="0" max="100" value={cloudLimit} onChange={e => setCloudLimit(e.target.value)} /></label>
        <button type="submit" className="btn-outline" disabled={loading || !bbox.trim()}><RefreshCw size={14} />{loading ? 'Finding scenes…' : 'Get NDVI'}</button>
      </div>
    </form>
    {error && <div className="error-banner" role="alert">{error}</div>}
    {loading && <div className="empty" role="status">Searching scene catalogue and calculating clear-pixel NDVI…</div>}
    {!loading && data && (active ? <>
      <div className="kpi-grid"><div className="kpi"><small>Mean NDVI</small><strong>{data.ndvi}</strong></div><div className="kpi"><small>Observation date</small><strong>{data.observation_date}</strong></div><div className="kpi"><small>Clear plot pixels</small><strong>{data.clear_pixel_coverage_pct}%</strong></div><div className="kpi"><small>Pixel resolution</small><strong>{data.resolution_meters} m</strong></div></div>
      <p className="microcopy">{data.source} · {data.scene_count} scenes · scene-wide cloud {data.cloud_cover_pct ?? 'unknown'}% · the clear-pixel percentage is plot-specific. This value is not a ground sensor or yield estimate and is not used in assessment.</p>
      {data.daily_series?.length > 1 && <details><summary>Daily NDVI observations</summary><div className="table-wrap"><table><thead><tr><th>Date</th><th>Mean NDVI</th><th>Clear pixel coverage</th><th>Valid pixels</th></tr></thead><tbody>{data.daily_series.map((row: any) => <tr key={row.date}><td>{row.date}</td><td>{row.mean_ndvi}</td><td>{row.clear_pixel_coverage_pct}%</td><td>{row.clear_pixel_count}</td></tr>)}</tbody></table></div></details>}
      <ul>{data.limitations?.map((item: string) => <li key={item}>{item}</li>)}</ul>
    </> : <div className="empty" role="status">{data.reason} {data.scene_count ? `${data.scene_count} intersecting scenes found; no NDVI value was calculated.` : ''}</div>)}
  </section>
}
