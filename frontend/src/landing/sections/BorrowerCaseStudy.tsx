import React from 'react'
import { SectionHeading } from '../components/SectionHeading'
import { DemoDataBadge } from '../components/DemoDataBadge'
import {
  User,
  AlertTriangle,
  Calendar,
  Wallet,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  FileText
} from 'lucide-react'

interface BorrowerCaseStudyProps {
  onNavigate: (page: string) => void
}

export function BorrowerCaseStudy({ onNavigate }: BorrowerCaseStudyProps) {
  return (
    <section className="landing-section case-study-section" id="case-study">
      <div className="landing-container">
        <SectionHeading
          tag="END-TO-END DEMONSTRATION"
          title="Synthetic Borrower Walkthrough: Overcoming a Due-Date Shock"
          subtitle="Follow a step-by-step scenario demonstrating how a temporary climate-linked cash delay is identified and restructured before bank delinquency occurs."
          badge={<DemoDataBadge type="synthetic" text="Synthetic Borrower B-DEMO-001" />}
        />

        <div className="case-study-card">
          {/* Top Profile Summary Bar */}
          <div className="case-profile-bar">
            <div className="case-profile-item">
              <span className="case-label">BORROWER</span>
              <b>Demo Farmer 001 (B-DEMO-001)</b>
              <small>Nashik Rural · Maharashtra</small>
            </div>
            <div className="case-profile-item">
              <span className="case-label">CROP & ACREAGE</span>
              <b>Maize · 2.4 Hectares</b>
              <small>Sowing: 20 Jun · Harvest: 10 Nov</small>
            </div>
            <div className="case-profile-item">
              <span className="case-label">FORMAL LOAN</span>
              <b>₹1,20,000 @ 12% p.a.</b>
              <small>Bank Due Date: 05 Nov 2026</small>
            </div>
            <div className="case-profile-badge">
              <DemoDataBadge type="synthetic" text="Synthetic Demo Profile" />
            </div>
          </div>

          {/* Chronological 4-Step Narrative */}
          <div className="case-steps-timeline">
            {/* Step 1 */}
            <div className="case-step-card">
              <div className="case-step-num">01</div>
              <div className="case-step-content">
                <span className="case-step-tag amber">CLIMATE SHOCK</span>
                <h4 className="case-step-title">4-Day Heatwave at Flowering</h4>
                <p className="case-step-desc">
                  An assumed 4-day temperature spike occurs during the flowering pollination window (Day 60). Yield estimate drops by 28% from 3.2 t/ha to 2.3 t/ha.
                </p>
                <div className="case-metric-chip">
                  <span>Impact:</span> <b>Yield -0.9 t/ha</b>
                </div>
              </div>
            </div>

            {/* Step 2 */}
            <div className="case-step-card">
              <div className="case-step-num">02</div>
              <div className="case-step-content">
                <span className="case-step-tag red">TIMING CONFLICT</span>
                <h4 className="case-step-title">Harvest Sale 5 Days Post-Due</h4>
                <p className="case-step-desc">
                  Mandi crop sale proceeds (+₹1,35,240) are realized on November 10th. However, the contractual loan payment of ₹1,24,000 is due on November 5th.
                </p>
                <div className="case-metric-chip danger">
                  <span>Due-Date Deficit:</span> <b>₹69,000 Cash Shortfall</b>
                </div>
              </div>
            </div>

            {/* Step 3 */}
            <div className="case-step-card">
              <div className="case-step-num">03</div>
              <div className="case-step-content">
                <span className="case-step-tag lime">INTERVENTION SIMULATION</span>
                <h4 className="case-step-title">Candidate Split Payment Evaluated</h4>
                <p className="case-step-desc">
                  The system models a split-installment proposal: ₹62,000 on Nov 5th (within available cash) and ₹64,295 on Dec 20th after harvest sales settle.
                </p>
                <div className="case-metric-chip lime">
                  <span>Resolved Gap:</span> <b>₹0 · Fee: +₹2,295</b>
                </div>
              </div>
            </div>

            {/* Step 4 */}
            <div className="case-step-card">
              <div className="case-step-num">04</div>
              <div className="case-step-content">
                <span className="case-step-tag green">AUDIT RECORD</span>
                <h4 className="case-step-title">Immutable Evaluation Snapshot</h4>
                <p className="case-step-desc">
                  The loan officer reviews the simulated trade-off, generates an audit snapshot with SHA-256 hash, and initiates formal bank review.
                </p>
                <div className="case-metric-chip">
                  <span>Hash:</span> <code>e8c47b91...</code>
                </div>
              </div>
            </div>
          </div>

          {/* Footer Action Bar */}
          <div className="case-footer-bar">
            <div className="case-footer-text">
              <b>Inspect this exact borrower scenario inside the live app</b>
              <p>Load the pre-configured walkthrough into the Scenario Lab.</p>
            </div>
            <button className="case-action-btn" onClick={() => onNavigate('scenarios')}>
              <span>Load Borrower Walkthrough</span>
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}
