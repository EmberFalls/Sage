import React, { useState } from 'react'
import { SectionHeading } from '../components/SectionHeading'
import { DemoDataBadge } from '../components/DemoDataBadge'
import {
  CloudSun,
  Wallet,
  TrendingDown,
  FileCheck,
  ChevronRight,
  ArrowRight,
  AlertTriangle,
  FileCode2,
  Calendar,
  Layers,
  Sparkles,
  ShieldCheck
} from 'lucide-react'

interface InteractiveFeaturesProps {
  onNavigate: (page: string) => void
}

export function InteractiveFeatures({ onNavigate }: InteractiveFeaturesProps) {
  const [activeTab, setActiveTab] = useState<'climate' | 'bridge' | 'multiseason' | 'audit'>('climate')

  return (
    <section className="landing-section features-walkthrough-section" id="platform-walkthrough">
      <div className="landing-container">
        <SectionHeading
          tag="WORKFLOW ARCHITECTURE"
          title="From weather anomaly to dated debt solvency"
          subtitle="Explore how PhenoCredit joins physiological crop sensitivity, bank repayment schedules, and carried debt across every stage of the lending lifecycle."
          badge={<DemoDataBadge type="synthetic" text="Interactive Preview" />}
        />

        {/* Tab Selection Bar */}
        <div className="features-tab-bar" role="tablist" aria-label="Feature Walkthrough Tabs">
          <button
            role="tab"
            aria-selected={activeTab === 'climate'}
            className={`features-tab-btn ${activeTab === 'climate' ? 'active' : ''}`}
            onClick={() => setActiveTab('climate')}
          >
            <CloudSun size={15} />
            <span>1. Climate Stress Engine</span>
          </button>

          <button
            role="tab"
            aria-selected={activeTab === 'bridge'}
            className={`features-tab-btn ${activeTab === 'bridge' ? 'active' : ''}`}
            onClick={() => setActiveTab('bridge')}
          >
            <Wallet size={15} />
            <span>2. Cash-Flow Bridge</span>
          </button>

          <button
            role="tab"
            aria-selected={activeTab === 'multiseason'}
            className={`features-tab-btn ${activeTab === 'multiseason' ? 'active' : ''}`}
            onClick={() => setActiveTab('multiseason')}
          >
            <TrendingDown size={15} />
            <span>3. 3-Season Debt Cycles</span>
          </button>

          <button
            role="tab"
            aria-selected={activeTab === 'audit'}
            className={`features-tab-btn ${activeTab === 'audit' ? 'active' : ''}`}
            onClick={() => setActiveTab('audit')}
          >
            <FileCheck size={15} />
            <span>4. Audit & Compliance</span>
          </button>
        </div>

        {/* Dynamic Tab Content Preview Cards */}
        <div className="features-preview-card">
          {/* TAB 1: CLIMATE STRESS ENGINE */}
          {activeTab === 'climate' && (
            <div className="tab-pane-grid">
              <div className="tab-pane-info">
                <span className="tab-eyebrow">MODULE 01 · PHENOLOGY MODELING</span>
                <h3 className="tab-title">Stage-Specific Sensitivity Calibration</h3>
                <p className="tab-desc">
                  PhenoCredit models crop growth in 5 distinct phenological windows (Planting, Vegetative, Flowering, Grain Fill, Harvest). High heat during flowering carries a 1.0× peak sensitivity multiplier compared to 0.25× during harvest.
                </p>
                <div className="tab-feature-bullets">
                  <div className="bullet-item">
                    <span className="bullet-dot" />
                    <span>Configurable rainfall variance (-60% drought to +25% flood)</span>
                  </div>
                  <div className="bullet-item">
                    <span className="bullet-dot" />
                    <span>Heatwave duration tracking with growth-stage assignment</span>
                  </div>
                  <div className="bullet-item">
                    <span className="bullet-dot" />
                    <span>Wheat & Maize specific physiological response curves</span>
                  </div>
                </div>
                <button className="tab-action-btn" onClick={() => onNavigate('climate')}>
                  <span>Open Climate Intelligence</span>
                  <ArrowRight size={14} />
                </button>
              </div>

              <div className="tab-pane-mockup">
                <div className="mockup-header">
                  <span>CLIMATE SENSITIVITY MATRIX · KHARIF MAIZE</span>
                  <DemoDataBadge type="assumed" text="Assumed Response Curve" />
                </div>
                <div className="mockup-stage-list">
                  <div className="mockup-stage-row">
                    <div className="stage-meta">
                      <b>Planting (Days 0–24)</b>
                      <small>20 Jun – 14 Jul · Base Index</small>
                    </div>
                    <div className="stage-bar-track">
                      <div className="stage-bar-fill" style={{ width: '45%' }} />
                    </div>
                    <span className="stage-weight">0.45×</span>
                  </div>

                  <div className="mockup-stage-row">
                    <div className="stage-meta">
                      <b>Vegetative (Days 25–54)</b>
                      <small>15 Jul – 13 Aug · Biomass Accumulation</small>
                    </div>
                    <div className="stage-bar-track">
                      <div className="stage-bar-fill" style={{ width: '65%' }} />
                    </div>
                    <span className="stage-weight">0.65×</span>
                  </div>

                  <div className="mockup-stage-row highlight-row">
                    <div className="stage-meta">
                      <b>Flowering (Days 55–75)</b>
                      <small>14 Aug – 03 Sep · Pollination Window</small>
                    </div>
                    <div className="stage-bar-track">
                      <div className="stage-bar-fill lime-fill" style={{ width: '100%' }} />
                    </div>
                    <span className="stage-weight lime-text">1.00× (Peak)</span>
                  </div>

                  <div className="mockup-stage-row">
                    <div className="stage-meta">
                      <b>Grain Fill (Days 76–112)</b>
                      <small>04 Sep – 10 Oct · Kernel Development</small>
                    </div>
                    <div className="stage-bar-track">
                      <div className="stage-bar-fill" style={{ width: '80%' }} />
                    </div>
                    <span className="stage-weight">0.80×</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: CASH FLOW BRIDGE */}
          {activeTab === 'bridge' && (
            <div className="tab-pane-grid">
              <div className="tab-pane-info">
                <span className="tab-eyebrow">MODULE 02 · DATED REPAYMENT LEDGER</span>
                <h3 className="tab-title">Dated Cash Available Before Contractual Due Date</h3>
                <p className="tab-desc">
                  A crop sale occurring on November 10th cannot settle an obligation due on November 5th. PhenoCredit creates a strict chronological cash-flow ledger that flags date-driven liquidity gaps before delinquency occurs.
                </p>
                <div className="tab-feature-bullets">
                  <div className="bullet-item">
                    <span className="bullet-dot" />
                    <span>Tracks initial cash, loan disbursement, input costs, and living costs</span>
                  </div>
                  <div className="bullet-item">
                    <span className="bullet-dot" />
                    <span>Enforces contractual cutoff date for harvest proceeds</span>
                  </div>
                  <div className="bullet-item">
                    <span className="bullet-dot" />
                    <span>Calculates exact INR shortfall required on due date</span>
                  </div>
                </div>
                <button className="tab-action-btn" onClick={() => onNavigate('assessment')}>
                  <span>View Credit Assessment</span>
                  <ArrowRight size={14} />
                </button>
              </div>

              <div className="tab-pane-mockup">
                <div className="mockup-header">
                  <span>DATED CASH BRIDGE · DEMO BORROWER B-001</span>
                  <DemoDataBadge type="synthetic" text="Synthetic Ledger" />
                </div>
                <div className="mockup-bridge-list">
                  <div className="bridge-step-row positive">
                    <span>Opening Cash & Disbursement</span>
                    <b>+ ₹1,35,000</b>
                  </div>
                  <div className="bridge-step-row negative">
                    <span>Input Costs (Seed, Fertilizer, Labor)</span>
                    <b>- ₹48,000</b>
                  </div>
                  <div className="bridge-step-row negative">
                    <span>Household Living Expenses</span>
                    <b>- ₹32,000</b>
                  </div>
                  <div className="bridge-step-row due-row">
                    <span>Bank Obligation Due (Nov 05)</span>
                    <b>₹1,24,000</b>
                  </div>
                  <div className="bridge-result-box shortfall">
                    <div>
                      <small>CASH AVAILABLE PRE-DUE</small>
                      <strong>₹55,000</strong>
                    </div>
                    <div>
                      <small>MODELED DUE-DATE GAP</small>
                      <strong className="danger-text">₹69,000 Shortfall</strong>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: 3-SEASON DEBT CYCLES */}
          {activeTab === 'multiseason' && (
            <div className="tab-pane-grid">
              <div className="tab-pane-info">
                <span className="tab-eyebrow">MODULE 03 · CARRIED LIABILITIES</span>
                <h3 className="tab-title">Preventing the Multi-Season Informal Debt Trap</h3>
                <p className="tab-desc">
                  When a farmer borrows from informal lenders to pay a bank due, the debt does not disappear. PhenoCredit models interest-accruing carried balances across 3 consecutive crop seasons.
                </p>
                <div className="tab-feature-bullets">
                  <div className="bullet-item">
                    <span className="bullet-dot" />
                    <span>Simulates formal bank arrears with interest compounding</span>
                  </div>
                  <div className="bullet-item">
                    <span className="bullet-dot" />
                    <span>Tracks informal bridge borrowing with priority settlement</span>
                  </div>
                  <div className="bullet-item">
                    <span className="bullet-dot" />
                    <span>Early warnings for persistent insolvency & negative equity</span>
                  </div>
                </div>
                <button className="tab-action-btn" onClick={() => onNavigate('scenarios')}>
                  <span>Simulate 3-Season Scenarios</span>
                  <ArrowRight size={14} />
                </button>
              </div>

              <div className="tab-pane-mockup">
                <div className="mockup-header">
                  <span>3-SEASON TOTAL DEBT PROJECTION (INR)</span>
                  <DemoDataBadge type="simulation" text="Simulation Only" />
                </div>
                <div className="mockup-season-cards">
                  <div className="season-card-mini">
                    <div className="season-title">Season 1 (Current)</div>
                    <div className="season-stat">
                      <small>Formal Bank</small>
                      <b>₹1,24,000</b>
                    </div>
                    <div className="season-stat">
                      <small>Informal Bridge</small>
                      <b className="amber-text">₹50,000</b>
                    </div>
                  </div>

                  <div className="season-card-mini">
                    <div className="season-title">Season 2 (Projected)</div>
                    <div className="season-stat">
                      <small>Formal Bank</small>
                      <b>₹1,20,000</b>
                    </div>
                    <div className="season-stat">
                      <small>Informal Bridge</small>
                      <b className="amber-text">₹72,500</b>
                    </div>
                  </div>

                  <div className="season-card-mini danger-border">
                    <div className="season-title">Season 3 (Carried)</div>
                    <div className="season-stat">
                      <small>Formal Bank</small>
                      <b>₹1,18,000</b>
                    </div>
                    <div className="season-stat">
                      <small>Informal Bridge</small>
                      <b className="danger-text">₹1,05,125</b>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: AUDIT & COMPLIANCE */}
          {activeTab === 'audit' && (
            <div className="tab-pane-grid">
              <div className="tab-pane-info">
                <span className="tab-eyebrow">MODULE 04 · TRANSPARENCY & AUDITING</span>
                <h3 className="tab-title">Cryptographically Hashed Evaluation Context</h3>
                <p className="tab-desc">
                  Every scenario assessment generates a deterministic SHA-256 context hash linking borrower parameters, climate overrides, and action proposals for underwriting compliance.
                </p>
                <div className="tab-feature-bullets">
                  <div className="bullet-item">
                    <span className="bullet-dot" />
                    <span>One-click export in standard JSON, CSV bridge ledger, or PDF format</span>
                  </div>
                  <div className="bullet-item">
                    <span className="bullet-dot" />
                    <span>Immutable comparison hash prevents retroactive parameter tampering</span>
                  </div>
                  <div className="bullet-item">
                    <span className="bullet-dot" />
                    <span>Full input provenance tracking (Verified, Assumed, Synthetic, Unavailable)</span>
                  </div>
                </div>
                <button className="tab-action-btn" onClick={() => onNavigate('watchlist')}>
                  <span>Open Reports & Snapshots</span>
                  <ArrowRight size={14} />
                </button>
              </div>

              <div className="tab-pane-mockup">
                <div className="mockup-header">
                  <span>AUDIT SNAPSHOT METADATA</span>
                  <DemoDataBadge type="verified" text="Deterministic SHA-256" />
                </div>
                <div className="mockup-audit-box">
                  <div className="audit-code-row">
                    <small>ENGINE VERSION</small>
                    <code>risk-engine-v2-demo.1</code>
                  </div>
                  <div className="audit-code-row">
                    <small>COMPARISON CONTEXT HASH</small>
                    <code>e8c47b91a2f6048d3c79e89b...</code>
                  </div>
                  <div className="audit-code-row">
                    <small>PROVENANCE STATUS</small>
                    <span className="audit-status-tag">8 / 8 FIN-03 Inputs Surface Tracked</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
