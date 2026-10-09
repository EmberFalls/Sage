import React from 'react'
import { SectionHeading } from '../components/SectionHeading'
import { DemoDataBadge } from '../components/DemoDataBadge'
import {
  ShieldCheck,
  Eye,
  UserCheck,
  Server,
  AlertTriangle,
  Lock,
  FileCheck2,
  Cpu
} from 'lucide-react'

export function TrustSection() {
  const trustPillars = [
    {
      icon: <Eye size={18} className="text-emerald-600" />,
      title: 'Full Input Provenance',
      desc: 'Every parameter in the system is explicitly tagged as verified, assumed, synthetic, or unavailable. No assumed values are ever disguised as real observations.',
    },
    {
      icon: <Cpu size={18} className="text-lime-600" />,
      title: 'Deterministic Explainability',
      desc: 'Formulas and sensitivity weights are fully auditable. The assessment engine produces deterministic outputs based solely on documented mathematical rules.',
    },
    {
      icon: <UserCheck size={18} className="text-blue-600" />,
      title: 'Human-in-the-Loop Governance',
      desc: 'PhenoCredit outputs are decision-support estimates. The system does not automate credit approvals, loan rejections, or binding contract modifications.',
    },
    {
      icon: <Server size={18} className="text-purple-600" />,
      title: 'CBS-Ready Architecture',
      desc: 'Designed around standard REST/JSON APIs and database-agnostic schemas (SQLite/PostgreSQL) for straightforward integration with core banking systems.',
    },
    {
      icon: <FileCheck2 size={18} className="text-teal-600" />,
      title: 'Cryptographic Snapshot Integrity',
      desc: 'Evaluations generate immutable SHA-256 context hashes, ensuring historical underwriting snapshots can be verified against retroactive alteration.',
    },
    {
      icon: <AlertTriangle size={18} className="text-amber-600" />,
      title: 'Explicit Claim Limits',
      desc: 'We clearly state that climate scenario controls represent hypothetical stress tests rather than issued meteorological predictions or calibrated default probabilities.',
    },
  ]

  return (
    <section className="landing-section trust-section" id="governance">
      <div className="landing-container">
        <SectionHeading
          tag="GOVERNANCE & TRUST"
          title="Institutional-Grade Transparency and Safety Controls"
          subtitle="Built from the ground up for bank risk committees, regulatory compliance, and responsible agricultural lending."
          badge={<DemoDataBadge type="verified" text="Governance Framework" />}
        />

        <div className="trust-grid">
          {trustPillars.map((pillar, idx) => (
            <div className="trust-card" key={idx}>
              <div className="trust-icon-box">{pillar.icon}</div>
              <h3 className="trust-card-title">{pillar.title}</h3>
              <p className="trust-card-desc">{pillar.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
