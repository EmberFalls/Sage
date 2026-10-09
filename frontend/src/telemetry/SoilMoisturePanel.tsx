import React, { useEffect, useState } from 'react'
import { RefreshCw, Droplets } from 'lucide-react'

const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export function SoilMoisturePanel({ district = 'Nashik' }: { district?: string; asOf?: string }) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const load = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API}/api/telemetry/soil-moisture?district=${encodeURIComponent(district)}`)
      if (!response.ok) throw new Error('Soil model data is unavailable')
      setData(await response.json())
    } catch { setData({ status: 'unavailable', reason: 'Soil model data could not be loaded.' }) }
    finally { setLoading(false) }
  }
  useEffect(() => { void load() }, [district])
  const active = data?.status === 'live_model_output'
  return <section className="card telemetry-card" aria-labelledby="soil-title">
    <div className="section-title"><div><h2 id="soil-title"><Droplets size={17} /> Soil moisture model</h2>
      <p>{active ? `${data.source} · ${data.district}` : 'District reference point · model output only'}</p></div>
      <button type="button" className="text-button" onClick={() => void load()} disabled={loading} aria-label="Refresh soil model data"><RefreshCw size={14} /></button></div>
    {loading && !data ? <div className="empty" role="status">Loading soil model data…</div> : active ? <>
      <p className="microcopy">Latest returned time: <b>{data.as_of}</b> · Not a farm sensor reading · Not used in assessment</p>
      <div className="table-wrap"><table><thead><tr><th>Layer</th><th>Depth</th><th>Model value</th></tr></thead><tbody>{data.layers.map((layer: any) => <tr key={layer.name}><td>{layer.name.replaceAll('_', ' ')}</td><td>{layer.depth}</td><td>{layer.value} {layer.unit}</td></tr>)}</tbody></table></div>
      {data.trend_history?.length > 0 && <details><summary>Recent model time series</summary><div className="table-wrap"><table><thead><tr><th>Time</th><th>Topsoil</th><th>Root zone</th><th>Subsoil</th></tr></thead><tbody>{data.trend_history.map((row: any) => <tr key={row.time}><td>{row.time}</td><td>{row.topsoil_volumetric_m3m3 ?? '—'}</td><td>{row.root_zone_volumetric_m3m3 ?? '—'}</td><td>{row.subsoil_volumetric_m3m3 ?? '—'}</td></tr>)}</tbody></table></div></details>}
      {data.forecast_history?.length > 0 && <details><summary>Upcoming modeled values</summary><div className="table-wrap"><table><thead><tr><th>Valid time</th><th>Topsoil</th><th>Root zone</th><th>Subsoil</th></tr></thead><tbody>{data.forecast_history.map((row: any) => <tr key={row.time}><td>{row.time}</td><td>{row.topsoil_volumetric_m3m3 ?? '—'}</td><td>{row.root_zone_volumetric_m3m3 ?? '—'}</td><td>{row.subsoil_volumetric_m3m3 ?? '—'}</td></tr>)}</tbody></table></div></details>}
      <ul>{data.limitations?.map((text: string) => <li key={text}>{text}</li>)}</ul>
    </> : <div className="empty" role="status">{data?.reason || 'Checking soil model availability…'} Soil telemetry remains separate from assessment results.</div>}
  </section>
}
