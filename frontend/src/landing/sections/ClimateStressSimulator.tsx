import React, { useState, useMemo } from 'react'
import { SectionHeading } from '../components/SectionHeading'
import { DemoDataBadge } from '../components/DemoDataBadge'
import { Sliders, RotateCcw, ArrowRight, TrendingDown, AlertTriangle, ShieldCheck, Gauge, Wallet, Sprout } from 'lucide-react'

interface ClimateStressSimulatorProps {
  onNavigate: (page: string) => void
}

export function ClimateStressSimulator({ onNavigate }: ClimateStressSimulatorProps) {
  // Simulator State
  const [rainfallPct, setRainfallPct] = useState<number>(0)
  const [heatwaveDays, setHeatwaveDays] = useState<number>(0)
  const [growthStage, setGrowthStage] = useState<'planting' | 'vegetative' | 'flowering' | 'grain_fill' | 'harvest'>('flowering')

  // Baseline Constants (Maize 2.4 ha synthetic borrower profile)
  const BASE_YIELD = 3.2 // tonnes per ha
  const FARM_AREA = 2.4 // ha
  const PRICE_PER_QUINTAL = 2450 // INR per quintal (1 tonne = 10 quintals)
  const LOAN_DUE_INR = 124000 // Principal + interest
  const BASE_PRE_DUE_CASH = 55000 // Cash available pre-due

  // Stage Sensitivity Multipliers (aligned with backend assessment engine)
  const STAGE_WEIGHTS: Record<string, number> = {
    planting: 0.45,
    vegetative: 0.65,
    flowering: 1.0,
    grain_fill: 0.8,
    harvest: 0.3,
  }

  // Deterministic calculation logic
  const calculatedOutputs = useMemo(() => {
    const weight = STAGE_WEIGHTS[growthStage] || 0.65

    // Rainfall stress impact (negative rain drops yield, extreme positive causes saturation)
    let rainLossPct = 0
    if (rainfallPct < 0) {
      rainLossPct = Math.abs(rainfallPct) * 0.7 * weight
    } else if (rainfallPct > 15) {
      rainLossPct = (rainfallPct - 15) * 0.4 * weight
    }

    // Heatwave stress impact (each day past 2 causes compounding damage in sensitive stages)
    const heatLossPct = Math.min(65, heatwaveDays * 4.2 * weight)

    // Total yield shock percentage
    const totalShockPct = Math.min(85, Math.max(0, rainLossPct + heatLossPct))
    const modeledYield = Math.max(0.4, BASE_YIELD * (1 - totalShockPct / 100))
    const totalHarvestTonnes = modeledYield * FARM_AREA
    const grossRevenue = totalHarvestTonnes * 10 * PRICE_PER_QUINTAL

    // Due date shortfall calculation:
    // If sale date is on/before due, revenue counts; otherwise pre-due cash shortfall occurs
    const effectiveCashPreDue = BASE_PRE_DUE_CASH
    const shortfall = Math.max(0, LOAN_DUE_INR - effectiveCashPreDue)

    // Repayment probability simulated estimation
    const feasibility = Math.max(12, Math.min(96, Math.round(94 - totalShockPct * 0.9)))

    return {
      totalShockPct: Math.round(totalShockPct),
      modeledYield: modeledYield.toFixed(2),
      grossRevenue: Math.round(grossRevenue),
      shortfall: Math.round(shortfall),
      feasibility,
    }
  }, [rainfallPct, heatwaveDays, growthStage])

  const handleReset = () => {
    setRainfallPct(0)
    setHeatwaveDays(0)
    setGrowthStage('flowering')
  }

  return (
    <section className="landing-section simulator-section" id="interactive-simulator">
      <div className="landing-container">
        <SectionHeading
          tag="HANDS-ON SIMULATION"
          title="Interactive Climate Stress Simulator"
          subtitle="Test how varying precipitation deficits and heatwaves during critical growth stages influence projected yield, mandi revenue, and repayment feasibility."
          badge={<DemoDataBadge type="simulation" text="Live Client-Side Calculator" />}
        />

        <div className="simulator-grid-card">
          {/* Controls Panel */}
          <div className="simulator-controls-col">
            <div className="sim-panel-header">
              <div className="sim-header-title">
                <Sliders size={16} />
                <span>Scenario Shock Controls</span>
              </div>
              <button className="sim-reset-btn" onClick={handleReset} title="Reset to baseline">
                <RotateCcw size={12} />
                <span>Reset</span>
              </button>
            </div>

            {/* Slider 1: Rainfall Variance */}
            <div className="sim-control-group">
              <div className="sim-control-label">
                <span>Rainfall Variance</span>
                <b className={`sim-val-pill ${rainfallPct < 0 ? 'negative' : rainfallPct > 0 ? 'positive' : ''}`}>
                  {rainfallPct > 0 ? `+${rainfallPct}%` : `${rainfallPct}%`}
                </b>
              </div>
              <input
                type="range"
                min="-60"
                max="25"
                step="5"
                value={rainfallPct}
                onChange={(e) => setRainfallPct(Number(e.target.value))}
                className="sim-slider"
                aria-label="Rainfall Variance Percentage"
              />
              <div className="sim-slider-ticks">
                <span>-60% (Drought)</span>
                <span>Normal</span>
                <span>+25% (Excess)</span>
              </div>
            </div>

            {/* Slider 2: Heatwave Days */}
            <div className="sim-control-group">
              <div className="sim-control-label">
                <span>Heatwave Duration</span>
                <b className={`sim-val-pill ${heatwaveDays > 3 ? 'danger' : ''}`}>
                  {heatwaveDays} {heatwaveDays === 1 ? 'day' : 'days'}
                </b>
              </div>
              <input
                type="range"
                min="0"
                max="14"
                step="1"
                value={heatwaveDays}
                onChange={(e) => setHeatwaveDays(Number(e.target.value))}
                className="sim-slider"
                aria-label="Heatwave Days"
              />
              <div className="sim-slider-ticks">
                <span>0 Days</span>
                <span>7 Days</span>
                <span>14 Days</span>
              </div>
            </div>

            {/* Select 3: Exposed Growth Stage */}
            <div className="sim-control-group">
              <div className="sim-control-label">
                <span>Exposed Growth Stage</span>
                <span className="sim-weight-badge">Weight: {STAGE_WEIGHTS[growthStage]}×</span>
              </div>
              <div className="sim-stage-buttons">
                {(['planting', 'vegetative', 'flowering', 'grain_fill', 'harvest'] as const).map((stage) => (
                  <button
                    key={stage}
                    type="button"
                    className={`sim-stage-btn ${growthStage === stage ? 'selected' : ''}`}
                    onClick={() => setGrowthStage(stage)}
                  >
                    {stage.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>

            <div className="sim-disclaimer-box">
              <AlertTriangle size={14} className="text-amber-500 flex-shrink-0" />
              <p>
                <b>Illustrative simulation:</b> Formulas demonstrate physiological stage sensitivity; not an issued weather prediction or calibrated agronomic forecast.
              </p>
            </div>
          </div>

          {/* Live Output Panel */}
          <div className="simulator-results-col">
            <div className="sim-panel-header">
              <span>Modeled Repayment Impact</span>
              <span className="sim-crop-badge">Kharif Maize · 2.4 ha</span>
            </div>

            <div className="sim-kpi-grid">
              {/* Output 1: Modeled Yield */}
              <div className="sim-kpi-card">
                <div className="sim-kpi-icon-wrap">
                  <Sprout size={16} />
                </div>
                <small>PROJECTED YIELD</small>
                <strong>
                  {calculatedOutputs.modeledYield} <span className="unit">t/ha</span>
                </strong>
                <span className={`sim-delta-tag ${calculatedOutputs.totalShockPct > 0 ? 'loss' : 'neutral'}`}>
                  {calculatedOutputs.totalShockPct > 0 ? `-${calculatedOutputs.totalShockPct}% Shock` : 'Baseline Level'}
                </span>
              </div>

              {/* Output 2: Feasibility */}
              <div className="sim-kpi-card">
                <div className="sim-kpi-icon-wrap">
                  <Gauge size={16} />
                </div>
                <small>REPAYMENT FEASIBILITY</small>
                <strong>{calculatedOutputs.feasibility}%</strong>
                <span className={`sim-delta-tag ${calculatedOutputs.feasibility >= 80 ? 'good' : 'warning'}`}>
                  {calculatedOutputs.feasibility >= 80 ? 'Low Risk' : 'Review Required'}
                </span>
              </div>

              {/* Output 3: Gross Revenue */}
              <div className="sim-kpi-card">
                <div className="sim-kpi-icon-wrap">
                  <Wallet size={16} />
                </div>
                <small>ESTIMATED CROP VALUE</small>
                <strong>₹{calculatedOutputs.grossRevenue.toLocaleString('en-IN')}</strong>
                <span className="sim-subtext">₹2,450 / quintal ref.</span>
              </div>

              {/* Output 4: Due Date Gap */}
              <div className="sim-kpi-card highlight-gap-card">
                <div className="sim-kpi-icon-wrap">
                  <TrendingDown size={16} />
                </div>
                <small>MODELED DUE-DATE GAP</small>
                <strong className="danger-text">₹{calculatedOutputs.shortfall.toLocaleString('en-IN')}</strong>
                <span className="sim-subtext">Pre-due cash deficit</span>
              </div>
            </div>

            {/* Transition CTA */}
            <div className="sim-action-banner">
              <div className="sim-banner-text">
                <b>Ready to test candidate interventions?</b>
                <p>Run full split-payment & due-date restructuring simulations inside the Scenario Lab.</p>
              </div>
              <button className="sim-primary-cta" onClick={() => onNavigate('scenarios')}>
                <span>Open in Workspace</span>
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
