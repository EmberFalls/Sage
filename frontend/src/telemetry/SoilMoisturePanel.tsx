import React, { useEffect, useState } from 'react'
import { Droplets, Gauge, RefreshCw, Thermometer, Layers } from 'lucide-react'

const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

interface SoilTelemetry {
  status: string
  source: string
  district: string
  topsoil_volumetric_m3m3: number
  root_zone_volumetric_m3m3: number
  subsoil_volumetric_m3m3: number
  soil_temperature_c: number
  field_capacity_m3m3: number
  wilting_point_m3m3: number
  water_stress_index: number
  moisture_condition: string
  trend_history: Array<{ time: string; topsoil: number; root_zone: number }>
}

export function SoilMoisturePanel({ district = 'Nashik', asOf = '2026-10-09' }: { district?: string; asOf?: string }) {
  const [data, setData] = useState<SoilTelemetry | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const fetchSoil = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API}/api/telemetry/soil-moisture?district=${encodeURIComponent(district)}&as_of=${encodeURIComponent(asOf)}`)
      if (!res.ok) throw new Error('Soil telemetry unavailable')
      const json = await res.json()
      setData(json)
    } catch (err: any) {
      setError(err.message || 'Could not fetch soil moisture telemetry')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSoil()
  }, [district, asOf])

  if (loading && !data) {
    return <div className="card empty" style={{ padding: '24px' }}>Loading Open-Meteo ERA5 soil moisture layers…</div>
  }

  if (error && !data) {
    return (
      <div className="card error-banner">
        <span>{error}</span>
        <button className="btn-outline" onClick={fetchSoil}>Retry</button>
      </div>
    )
  }

  const topsoilPct = Math.round((data?.topsoil_volumetric_m3m3 || 0.28) * 100)
  const rootZonePct = Math.round((data?.root_zone_volumetric_m3m3 || 0.32) * 100)
  const subsoilPct = Math.round((data?.subsoil_volumetric_m3m3 || 0.35) * 100)
  const aswScore = Math.round((data?.water_stress_index || 0.75) * 100)

  return (
    <section className="card telemetry-card">
      <div className="section-title">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h2 style={{ fontSize: '1.05rem', margin: 0, display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Droplets size={18} style={{ color: '#38bdf8' }} /> Soil Moisture & Root-Zone Hydrology
            </h2>
            <span className="tag green" style={{ fontSize: '0.65rem' }}>LIVE OPEN-METEO</span>
          </div>
          <p style={{ margin: '4px 0 0', fontSize: '0.78rem', color: '#94a3b8' }}>
            {data?.source || 'ERA5-Land 9km Land Surface Model'} · {data?.district || district}
          </p>
        </div>
        <button className="text-button" onClick={fetchSoil} title="Refresh live telemetry" disabled={loading}>
          <RefreshCw size={13} className={loading ? 'spin' : ''} />
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '10px', marginTop: '12px' }}>
        <div style={{ background: 'rgba(56, 189, 248, 0.07)', border: '1px solid rgba(56, 189, 248, 0.2)', borderRadius: '10px', padding: '10px' }}>
          <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Topsoil (0–7 cm)</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#38bdf8', margin: '3px 0' }}>{topsoilPct}% <small style={{ fontSize: '0.7rem', fontWeight: 400 }}>vol</small></div>
          <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Seedbed moisture</div>
        </div>

        <div style={{ background: 'rgba(34, 197, 94, 0.07)', border: '1px solid rgba(34, 197, 94, 0.2)', borderRadius: '10px', padding: '10px' }}>
          <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Root Zone (7–28 cm)</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#4ade80', margin: '3px 0' }}>{rootZonePct}% <small style={{ fontSize: '0.7rem', fontWeight: 400 }}>vol</small></div>
          <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Crop transpiration zone</div>
        </div>

        <div style={{ background: 'rgba(148, 163, 184, 0.07)', border: '1px solid rgba(148, 163, 184, 0.15)', borderRadius: '10px', padding: '10px' }}>
          <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Subsoil (28–100 cm)</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#e2e8f0', margin: '3px 0' }}>{subsoilPct}% <small style={{ fontSize: '0.7rem', fontWeight: 400 }}>vol</small></div>
          <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Deep reservoir</div>
        </div>

        <div style={{ background: 'rgba(251, 146, 60, 0.07)', border: '1px solid rgba(251, 146, 60, 0.2)', borderRadius: '10px', padding: '10px' }}>
          <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Soil Temp</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fb923c', margin: '3px 0', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Thermometer size={16} /> {data?.soil_temperature_c || 26.4}°C
          </div>
          <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Optimum root temp</div>
        </div>
      </div>

      <div style={{ marginTop: '14px', background: 'rgba(15, 23, 42, 0.5)', borderRadius: '10px', padding: '12px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
          <span style={{ fontSize: '0.75rem', color: '#cbd5e1', fontWeight: 500 }}>Relative Available Soil Water (ASW Index):</span>
          <span className="tag green" style={{ fontSize: '0.7rem' }}>{data?.moisture_condition || 'Optimum Field Moisture'} ({aswScore}%)</span>
        </div>
        <div style={{ width: '100%', height: '8px', background: '#334155', borderRadius: '4px', overflow: 'hidden' }}>
          <div style={{ width: `${Math.min(100, aswScore)}%`, height: '100%', background: aswScore > 40 ? 'linear-gradient(90deg, #38bdf8, #22c55e)' : '#f59e0b', borderRadius: '4px' }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px', fontSize: '0.68rem', color: '#64748b' }}>
          <span>Wilting Point ({Math.round((data?.wilting_point_m3m3 || 0.15) * 100)}%)</span>
          <span>Field Capacity ({Math.round((data?.field_capacity_m3m3 || 0.36) * 100)}%)</span>
        </div>
      </div>
    </section>
  )
}
