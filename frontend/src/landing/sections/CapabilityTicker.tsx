import React from 'react'
import { CloudSun, Sprout, CalendarClock, ShieldAlert, FileCode2, Database } from 'lucide-react'
import { DemoDataBadge } from '../components/DemoDataBadge'

export function CapabilityTicker() {
  const capabilities = [
    {
      icon: <CloudSun size={18} />,
      title: '5-Stage Climate Shocks',
      desc: 'Planting to harvest heatwave & precipitation anomaly modeling',
    },
    {
      icon: <CalendarClock size={18} />,
      title: 'Dated Pre-Due Cash Ledger',
      desc: 'Sales after the bank due date are strictly excluded from due cash',
    },
    {
      icon: <ShieldAlert size={18} />,
      title: 'Early Warning Engine',
      desc: 'Rule-backed detection of informal debt cycles & liquidity shortfalls',
    },
    {
      icon: <Sprout size={18} />,
      title: 'Candidate Interventions',
      desc: 'Compare +30d reschedule vs split payments with fee trade-offs',
    },
    {
      icon: <FileCode2 size={18} />,
      title: 'Audit-Grade Hashes',
      desc: 'Deterministic SHA-256 context hashing on every scenario evaluation',
    },
    {
      icon: <Database size={18} />,
      title: '8-Group FIN-03 Coverage',
      desc: 'Explicit tracking of verified vs assumed environmental and loan inputs',
    },
  ]

  return (
    <section className="capability-ticker-section" aria-label="Platform Core Capabilities">
      <div className="capability-ticker-container">
        <div className="capability-header-bar">
          <div className="capability-status-label">
            <span className="live-engine-indicator" />
            <span>PLATFORM CAPABILITIES · FIN-03 ARCHITECTURE</span>
          </div>
          <DemoDataBadge type="synthetic" text="Seeded SQLite Demo Engine" />
        </div>

        <div className="capability-grid">
          {capabilities.map((cap, idx) => (
            <div className="capability-card" key={idx}>
              <div className="capability-icon-wrap">{cap.icon}</div>
              <div className="capability-text-wrap">
                <h3 className="capability-title">{cap.title}</h3>
                <p className="capability-desc">{cap.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
