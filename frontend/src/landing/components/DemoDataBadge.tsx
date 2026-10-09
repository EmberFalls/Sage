import React from 'react'
import { ShieldCheck, Sparkles, Info } from 'lucide-react'

interface DemoDataBadgeProps {
  type?: 'synthetic' | 'assumed' | 'verified' | 'simulation' | 'provisional'
  text?: string
}

export function DemoDataBadge({ type = 'synthetic', text }: DemoDataBadgeProps) {
  const configs = {
    synthetic: { label: text || 'Synthetic demo record', class: 'badge-synthetic', icon: <ShieldCheck size={12} /> },
    assumed: { label: text || 'Assumed scenario input', class: 'badge-assumed', icon: <Info size={12} /> },
    verified: { label: text || 'Verified API reanalysis', class: 'badge-verified', icon: <Sparkles size={12} /> },
    simulation: { label: text || 'Illustrative simulation · uncalibrated', class: 'badge-simulation', icon: <Info size={12} /> },
    provisional: { label: text || 'Proposed pilot packaging', class: 'badge-provisional', icon: <Info size={12} /> },
  }

  const current = configs[type] || configs.synthetic

  return (
    <span className={`demo-badge-pill ${current.class}`} title="Data Provenance Status">
      {current.icon}
      <span>{current.label}</span>
    </span>
  )
}
