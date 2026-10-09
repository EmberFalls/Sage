import React from 'react'
import { SectionHeading } from '../components/SectionHeading'
import { DemoDataBadge } from '../components/DemoDataBadge'
import {
  Satellite,
  CloudSun,
  Sprout,
  Database,
  Layers,
  ArrowRight,
  TrendingUp,
  FileCheck2,
  Lock,
  CheckCircle2,
  Clock,
  HelpCircle
} from 'lucide-react'

export function DataPipeline() {
  const inputNodes = [
    {
      title: 'Satellite / NDVI',
      source: 'Sentinel-2 / MODIS (Planned)',
      status: 'Unavailable',
      statusType: 'neutral',
      desc: 'Vegetation index telemetry; currently bypassed in demo mode',
      icon: <Satellite size={16} />,
    },
    {
      title: 'Weather Forecast & Shocks',
      source: 'Open-Meteo Reanalysis / Scenario Controls',
      status: 'Assumed Scenario',
      statusType: 'olive',
      desc: 'Heatwave duration & precipitation percentage anomaly',
      icon: <CloudSun size={16} />,
    },
    {
      title: 'Crop Growth Windows',
      source: 'Physiological Stage Calendar',
      status: 'Assumed Calendar',
      statusType: 'olive',
      desc: '5 growth stages with differential drought/heat sensitivity weights',
      icon: <Sprout size={16} />,
    },
    {
      title: 'Mandi Market Reference',
      source: 'Price Reference Schedule',
      status: 'Assumed Input',
      statusType: 'olive',
      desc: 'Commodity price assumption (e.g. ₹2,450/q for Maize)',
      icon: <TrendingUp size={16} />,
    },
    {
      title: 'Soil Moisture & Evapotranspiration',
      source: 'Soil Profile (Planned)',
      status: 'Unavailable',
      statusType: 'neutral',
      desc: 'Sub-surface root zone hydration; not used by current model',
      icon: <Layers size={16} />,
    },
    {
      title: 'Loan Ledger & Due Schedule',
      source: 'Local SQLite Database',
      status: 'Synthetic Demo Record',
      statusType: 'amber',
      desc: 'Synthetic borrower principal, interest rates, and contractual due dates',
      icon: <Database size={16} />,
    },
  ]

  const workflowSteps = [
    { step: '01', title: 'Input Ingestion', desc: 'Normalizes synthetic ledger events and scenario weather parameters' },
    { step: '02', title: 'Stage Sensitivity', desc: 'Applies crop-specific vulnerability multipliers by growth window' },
    { step: '03', title: 'Dated Cash Ledger', desc: 'Enforces strict contractual repayment cutoff for harvest revenue' },
    { step: '04', title: 'Solvency & Gap Analysis', desc: 'Derives pre-due shortfall and multi-season debt accumulation' },
    { step: '05', title: 'Cryptographic Hashing', desc: 'Generates SHA-256 context hash for verifiable underwriting audit' },
  ]

  return (
    <section className="landing-section data-pipeline-section" id="data-pipeline">
      <div className="landing-container">
        <SectionHeading
          tag="DATA GOVERNANCE & PROVENANCE"
          title="Transparent FIN-03 Input-to-Decision Architecture"
          subtitle="Every output is explicitly linked to its underlying source status. PhenoCredit clearly distinguishes verified telemetry, assumed parameters, and synthetic records."
          badge={<DemoDataBadge type="verified" text="Transparent Provenance Model" />}
        />

        {/* Legend Bar */}
        <div className="pipeline-legend-bar">
          <span className="legend-item">
            <span className="legend-dot green" />
            <span>Verified Live Data</span>
          </span>
          <span className="legend-item">
            <span className="legend-dot olive" />
            <span>Assumed Scenario Input</span>
          </span>
          <span className="legend-item">
            <span className="legend-dot amber" />
            <span>Synthetic Demo Profile</span>
          </span>
          <span className="legend-item">
            <span className="legend-dot neutral" />
            <span>Currently Unavailable / Planned</span>
          </span>
        </div>

        {/* 6-Node Input Grid */}
        <div className="pipeline-nodes-grid">
          {inputNodes.map((node, i) => (
            <div className={`pipeline-node-card status-${node.statusType}`} key={i}>
              <div className="node-card-top">
                <div className="node-icon-wrap">{node.icon}</div>
                <span className={`node-status-pill pill-${node.statusType}`}>{node.status}</span>
              </div>
              <h3 className="node-title">{node.title}</h3>
              <small className="node-source">{node.source}</small>
              <p className="node-desc">{node.desc}</p>
            </div>
          ))}
        </div>

        {/* Workflow Progression Strip */}
        <div className="pipeline-workflow-container">
          <div className="workflow-title-bar">
            <span>CORE ASSESSMENT PIPELINE</span>
            <small>Deterministic Assessment Engine</small>
          </div>
          <div className="workflow-steps-row">
            {workflowSteps.map((ws, i) => (
              <div className="workflow-step-box" key={i}>
                <span className="workflow-num">{ws.step}</span>
                <b className="workflow-step-title">{ws.title}</b>
                <p className="workflow-step-desc">{ws.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
