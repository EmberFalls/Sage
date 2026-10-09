import React from 'react'
import { SectionHeading } from '../components/SectionHeading'
import { DemoDataBadge } from '../components/DemoDataBadge'
import { AlertCircle, TrendingDown, Clock, ShieldCheck, ArrowRight, ArrowDownRight, Layers } from 'lucide-react'

interface BentoGridProps {
  onNavigate: (page: string) => void
}

export function BentoGrid({ onNavigate }: BentoGridProps) {
  return (
    <section className="landing-section bento-section" id="problem-solution">
      <div className="landing-container">
        <SectionHeading
          tag="THE LENDING GAP"
          title="Why traditional credit scoring fails in agrarian portfolios"
          subtitle="Conventional underwriting checks historical debt records. PhenoCredit links in-season climate shocks directly to dated cash flow and contractual bank due dates."
          badge={<DemoDataBadge type="assumed" text="Scenario Evidence Model" />}
        />

        <div className="bento-grid-wrapper">
          {/* Tile A: The Climate Blind Spot (Dark Surface) */}
          <div className="bento-tile tile-dark tile-blindspot">
            <div className="bento-tile-badge">
              <AlertCircle size={13} className="text-amber-400" />
              <span>THE BLIND SPOT</span>
            </div>
            <h3 className="bento-tile-title">Conventional bureaus only see the past.</h3>
            <p className="bento-tile-desc">
              A borrower with a spotless historical repayment record can still default when a 4-day heatwave hits during flowering. By the time a missed EMI registers, the debt spiral has already begun.
            </p>

            <div className="bento-blindspot-comparison">
              <div className="bento-comp-item dim">
                <span className="bento-comp-tag">Standard Bureau</span>
                <strong>Credit Score 780</strong>
                <small>Checks past seasons only · ignores weather</small>
              </div>
              <div className="bento-comp-arrow">
                <ArrowRight size={16} />
              </div>
              <div className="bento-comp-item highlight">
                <span className="bento-comp-tag lime">PhenoCredit View</span>
                <strong>High Stress @ Flowering</strong>
                <small>Yield -38% · ₹42,000 cash shortfall projected</small>
              </div>
            </div>
          </div>

          {/* Tile B: Crop-Stage & Climate Context */}
          <div className="bento-tile tile-light tile-stages">
            <div className="bento-tile-badge">
              <Layers size={13} />
              <span>STAGE SENSITIVITY</span>
            </div>
            <h3 className="bento-tile-title">Timing matters more than total rainfall.</h3>
            <p className="bento-tile-desc">
              100mm of rain during vegetative growth creates healthy biomass, but the same moisture deficit during grain fill destroys harvest yield.
            </p>

            <div className="bento-stages-bar">
              <div className="bento-stage-chip">
                <span>Planting</span>
                <b>0.45x</b>
              </div>
              <div className="bento-stage-chip">
                <span>Vegetative</span>
                <b>0.65x</b>
              </div>
              <div className="bento-stage-chip peak">
                <span>Flowering</span>
                <b>1.00x</b>
                <small className="peak-tag">Max Impact</small>
              </div>
              <div className="bento-stage-chip">
                <span>Grain Fill</span>
                <b>0.80x</b>
              </div>
            </div>
          </div>

          {/* Tile C: Harvest-to-Repayment Timing */}
          <div className="bento-tile tile-light tile-timing">
            <div className="bento-tile-badge">
              <Clock size={13} />
              <span>CASH FLOW TIMING</span>
            </div>
            <h3 className="bento-tile-title">The Due-Date Cash Mismatch</h3>
            <p className="bento-tile-desc">
              If the crop sells on Nov 10th but the bank loan is due on Nov 5th, the borrower has a ₹0 cash balance on the due date—forcing them into informal moneylenders.
            </p>

            <div className="bento-timeline-strip">
              <div className="bento-time-event due">
                <span className="dot" />
                <small>Nov 05</small>
                <b>Bank Due Date</b>
                <span>₹1,24,000 Due</span>
              </div>
              <div className="bento-time-gap">
                <span>5-Day Gap</span>
              </div>
              <div className="bento-time-event sale">
                <span className="dot" />
                <small>Nov 10</small>
                <b>Mandi Crop Sale</b>
                <span>+ ₹1,85,000 Revenue</span>
              </div>
            </div>
          </div>

          {/* Tile D: Early Intervention Options (Lime Accent Surface) */}
          <div className="bento-tile tile-lime tile-interventions">
            <div className="bento-tile-badge">
              <ShieldCheck size={13} />
              <span>HUMAN-IN-THE-LOOP ACTIONS</span>
            </div>
            <h3 className="bento-tile-title">Pre-delinquency restructuring.</h3>
            <p className="bento-tile-desc">
              Evaluate simulated proposals—such as +30-day rescheduling or split installments—with transparent extra fee calculations before formal default triggers.
            </p>

            <div className="bento-action-preview">
              <div className="bento-action-pill">
                <span>Reschedule +30 Days</span>
                <b>Gap ₹0 · +₹1,183 Interest</b>
              </div>
              <div className="bento-action-pill">
                <span>Split Payment 50/50</span>
                <b>Gap ₹0 · +₹2,295 Fee</b>
              </div>
            </div>

            <button className="bento-explore-btn" onClick={() => onNavigate('interventions')}>
              <span>Explore Intervention Center</span>
              <ArrowRight size={13} />
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}
