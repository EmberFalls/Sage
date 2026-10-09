import React from 'react'
import { ArrowRight, Layers, ShieldCheck, Database, FileText, Globe } from 'lucide-react'

interface LandingFooterProps {
  onNavigate: (page: string) => void
}

export function LandingFooter({ onNavigate }: LandingFooterProps) {
  const scrollTo = (id: string) => {
    const el = document.getElementById(id)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' })
    }
  }

  return (
    <footer className="landing-footer-section">
      <div className="landing-container">
        {/* Conversion Banner Card */}
        <div className="footer-conversion-card">
          <div className="conversion-card-content">
            <span className="conversion-tag">START EXPLORING</span>
            <h2 className="conversion-title">Bring climate context into agricultural credit decisions.</h2>
            <p className="conversion-subtitle">
              Explore the full interactive workspace, test scenario shocks across synthetic borrower portfolios, and evaluate candidate restructuring proposals.
            </p>
            <div className="conversion-btn-row">
              <button className="footer-primary-cta" onClick={() => onNavigate('overview')}>
                <span>Launch Interactive Workspace</span>
                <ArrowRight size={15} />
              </button>
              <button className="footer-secondary-cta" onClick={() => scrollTo('interactive-simulator')}>
                <span>Try Climate Simulator</span>
              </button>
            </div>
          </div>
        </div>

        {/* Footer Navigation Columns */}
        <div className="footer-links-grid">
          {/* Col 1: Brand & Info */}
          <div className="footer-brand-col">
            <div className="footer-brand-logo" onClick={() => onNavigate('landing')} role="button" tabIndex={0}>
              <div className="footer-brand-icon">
                <Layers size={18} strokeWidth={2.4} />
              </div>
              <span className="footer-brand-name">Sage</span>
            </div>
            <p className="footer-brand-desc">
              A climate-aware agricultural credit risk assessment & lending intelligence platform linking in-season weather shocks to dated borrower cash flows.
            </p>
            <div className="footer-status-pill">
              <span className="status-live-dot" />
              <span>Offline Ready · Seed 20261009</span>
            </div>
          </div>

          {/* Col 2: Platform Links */}
          <div className="footer-nav-col">
            <span className="footer-col-title">WORKSPACE</span>
            <button className="footer-link-btn" onClick={() => onNavigate('overview')}>Portfolio Overview</button>
            <button className="footer-link-btn" onClick={() => onNavigate('borrowers')}>Borrower Registry</button>
            <button className="footer-link-btn" onClick={() => onNavigate('loans')}>Loan Records Ledger</button>
            <button className="footer-link-btn" onClick={() => onNavigate('farmer')}>Farmer Loan Summary</button>
          </div>

          {/* Col 3: Intelligence & Labs */}
          <div className="footer-nav-col">
            <span className="footer-col-title">INTELLIGENCE</span>
            <button className="footer-link-btn" onClick={() => onNavigate('climate')}>Climate Intelligence</button>
            <button className="footer-link-btn" onClick={() => onNavigate('assessment')}>Credit Assessment</button>
            <button className="footer-link-btn" onClick={() => onNavigate('scenarios')}>Scenario Lab</button>
            <button className="footer-link-btn" onClick={() => onNavigate('interventions')}>Intervention Center</button>
          </div>

          {/* Col 4: Governance & Reports */}
          <div className="footer-nav-col">
            <span className="footer-col-title">GOVERNANCE</span>
            <button className="footer-link-btn" onClick={() => onNavigate('watchlist')}>Reports & Snapshots</button>
            <button className="footer-link-btn" onClick={() => onNavigate('methodology')}>Data & Methodology</button>
            <button className="footer-link-btn" onClick={() => scrollTo('governance')}>Governance & Trust</button>
            <button className="footer-link-btn" onClick={() => scrollTo('faq')}>Frequently Asked Questions</button>
          </div>
        </div>

        {/* Bottom Bar with Regulatory Disclaimer */}
        <div className="footer-bottom-bar">
          <p className="footer-disclaimer-text">
            <b>Disclaimer:</b> Sage is an agricultural credit-risk decision-support prototype (PS 3). Output metrics, repayment feasibility scores, and shortfall estimates are simulation outputs derived from synthetic loan portfolios and assumed meteorological parameters. They do not constitute binding credit approvals, formal banking advice, or crop performance guarantees.
          </p>
          <div className="footer-meta-row">
            <span>© 2026 Sage Platform · All Rights Reserved</span>
            <span>FIN-03 Architecture</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
