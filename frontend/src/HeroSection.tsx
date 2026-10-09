import React from 'react'
import {
  ArrowRight,
  ChevronRight,
  Droplets,
  ShieldCheck,
  Sprout,
  Sun,
  TrendingUp,
  Layers
} from 'lucide-react'

import { useAuth } from './auth/AuthContext'

interface HeroSectionProps {
  onNavigate: (page: string) => void
}

export function HeroSection({ onNavigate }: HeroSectionProps) {
  const { user, isAuthenticated, logout } = useAuth()
  return (
    <div className="hero-viewport">
      {/* Background Image & Atmospheric Color Grading */}
      <div className="hero-backdrop" />
      <div className="hero-gradient-overlay" />

      {/* Centered Apple-Style Floating Glass Island Navbar */}
      <header className="hero-nav-wrapper">
        <nav className="hero-apple-navbar" aria-label="Main Navigation">
          {/* Brand Segment */}
          <div 
            className="hero-brand" 
            onClick={() => onNavigate('landing')} 
            role="button" 
            tabIndex={0}
            title="Sage Home"
          >
            <div className="hero-brand-icon">
              <Layers size={18} strokeWidth={2.4} />
            </div>
            <span className="hero-brand-name">Sage</span>
          </div>

          <div className="hero-nav-divider" />

          {/* Navigation Links */}
          <div className="hero-nav-links">
            <button className="hero-nav-link active" onClick={() => onNavigate('landing')}>
              Home
            </button>
            <button className="hero-nav-link" onClick={() => onNavigate(user?.role === 'farmer' ? 'farmer' : 'overview')}>
              Platform
            </button>
            <button className="hero-nav-link" onClick={() => onNavigate('methodology')}>
              How It Works
            </button>
            <button className="hero-nav-link" onClick={() => onNavigate('scenarios')}>
              Insights
            </button>
            <button className="hero-nav-link" onClick={() => onNavigate('methodology')}>
              About
            </button>
          </div>

          <div className="hero-nav-divider" />

          {/* Right Action / CTA Segment */}
          <div className="hero-nav-actions">
            {isAuthenticated && user ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button
                  className="hero-apple-cta"
                  onClick={() => onNavigate(user.role === 'farmer' ? 'farmer' : 'overview')}
                  title={`Logged in as ${user.name}`}
                  style={{ background: 'rgba(16, 185, 129, 0.25)', borderColor: 'rgba(52, 211, 153, 0.4)' }}
                >
                  <span>{user.role === 'farmer' ? 'Farmer Portal' : 'Workspace'}</span>
                  <ArrowRight size={13} strokeWidth={2.4} />
                </button>
              </div>
            ) : (
              <>
                <button className="hero-nav-link" style={{ fontWeight: 600, color: '#38bdf8' }} onClick={() => onNavigate('login')}>
                  Sign In
                </button>
                <button className="hero-apple-cta" onClick={() => onNavigate('login')}>
                  <span>Get Started</span>
                  <ArrowRight size={13} strokeWidth={2.4} />
                </button>
              </>
            )}
          </div>
        </nav>
      </header>

      {/* Hero Content Area */}
      <main className="hero-content-wrapper">
        {/* Massive Editorial Headline */}
        <h1 className="hero-headline">
          Climate risk,<br />
          clearly understood.
        </h1>

        {/* Floating Dashboard Card Cluster with Staggered Bounce Entrance */}
        <section className="hero-cards-cluster" aria-label="Interactive Climate Risk Intelligence Cards">
          {/* Left Column: Stacked Card A and Card B */}
          <div className="hero-cards-left-col">
            {/* Card A: Climate Snapshot */}
            <article 
              className="hero-card hero-card-snapshot anim-bounce-1" 
              onClick={() => onNavigate('climate')}
              title="Inspect Climate Telemetry"
            >
              <div className="hero-card-header">
                <div className="hero-card-title-group">
                  <h3 className="hero-card-title">Climate snapshot</h3>
                  <span className="hero-card-subtitle">TELEMETRY · PUNE REGION</span>
                </div>
                <div className="hero-card-live-chip">
                  <span className="hero-pulse-dot" />
                  <span>LIVE</span>
                </div>
              </div>

              <div className="hero-snapshot-indicators">
                {/* Indicator 1: Rainfall */}
                <div className="hero-dial-item">
                  <div className="hero-dial-circle dial-rainfall">
                    <Droplets size={14} className="dial-icon icon-rain" />
                    <div className="dial-num-wrap">
                      <span className="dial-value">92</span>
                      <span className="dial-unit">mm</span>
                    </div>
                  </div>
                  <span className="dial-label">RAINFALL</span>
                  <span className="dial-status-text">Normal</span>
                </div>

                {/* Indicator 2: Crop Health */}
                <div className="hero-dial-item">
                  <div className="hero-dial-circle dial-crop">
                    <Sprout size={14} className="dial-icon icon-crop" />
                    <div className="dial-num-wrap">
                      <span className="dial-value">0.84</span>
                      <span className="dial-unit">NDVI</span>
                    </div>
                  </div>
                  <span className="dial-label">CROP HEALTH</span>
                  <span className="dial-status-text text-optimal">Optimal</span>
                </div>

                {/* Indicator 3: Heat Stress */}
                <div className="hero-dial-item">
                  <div className="hero-dial-circle dial-heat">
                    <Sun size={14} className="dial-icon icon-heat" />
                    <div className="dial-num-wrap">
                      <span className="dial-value">28°</span>
                      <span className="dial-unit">C</span>
                    </div>
                  </div>
                  <span className="dial-label">HEAT STRESS</span>
                  <span className="dial-status-text">Low</span>
                </div>
              </div>
            </article>

            {/* Card B: Borrower Outlook */}
            <article 
              className="hero-card hero-card-borrower anim-bounce-2" 
              onClick={() => onNavigate('assessment')}
              title="Inspect Borrower Assessment"
            >
              <div className="hero-card-header">
                <div className="hero-card-title-group">
                  <h3 className="hero-card-title">Borrower outlook</h3>
                  <span className="hero-card-subtitle">PORTFOLIO RISK PROFILE</span>
                </div>
                <span className="hero-id-tag">B-DEMO-001</span>
              </div>

              <div className="hero-borrower-body">
                <div className="hero-borrower-kpi-row">
                  <div className="hero-shield-emblem">
                    <ShieldCheck size={20} strokeWidth={2.2} />
                  </div>
                  <div className="hero-borrower-kpi-text">
                    <span className="hero-kpi-micro-label">CLIMATE-ADJUSTED RISK</span>
                    <div className="hero-feasibility-stat">
                      <span className="hero-feasibility-num">94%</span>
                      <span className="hero-feasibility-badge">Repayment Feasibility</span>
                    </div>
                  </div>
                </div>

                <div className="hero-borrower-meta-strip">
                  <span className="hero-tag-pill">Maize · 2.4 ha</span>
                  <span className="hero-tag-pill highlight-gap">Modeled Gap: ₹0</span>
                  <span className="hero-tag-pill">Pune Dist.</span>
                </div>
              </div>
            </article>
          </div>

          {/* Right Column: Card C (Climate Impact Chart Card) */}
          <div className="hero-cards-right-col">
            <article 
              className="hero-card hero-card-impact anim-bounce-3" 
              onClick={() => onNavigate('scenarios')}
              title="Open Scenario Simulation"
            >
              <div className="hero-card-header">
                <div className="hero-card-title-group">
                  <h3 className="hero-card-title">Climate impact</h3>
                  <span className="hero-card-subtitle">STAGE RESILIENCE PROJECTION</span>
                </div>
                <div className="hero-gain-badge">
                  <TrendingUp size={12} strokeWidth={2.5} />
                  <span>+14% vs Base</span>
                </div>
              </div>

              {/* 4-Bar Modern Vertical Chart */}
              <div className="hero-impact-chart">
                {/* Floating Apple-Style Tooltip over Growth Bar */}
                <div className="hero-chart-callout">
                  <div className="hero-callout-pill">
                    <span className="hero-callout-tag">RISK OUTLOOK</span>
                    <span className="hero-callout-title">Peak resilience</span>
                  </div>
                  <div className="hero-callout-pointer" />
                </div>

                <div className="hero-bars-track-area">
                  {/* Bar 1: Baseline */}
                  <div className="hero-chart-bar-group">
                    <div className="hero-bar-well">
                      <div className="hero-bar-column bar-dark anim-bar-1" style={{ height: '54%' }}>
                        <span className="hero-bar-val">54%</span>
                      </div>
                    </div>
                    <span className="hero-axis-label">Baseline</span>
                  </div>

                  {/* Bar 2: Sowing */}
                  <div className="hero-chart-bar-group">
                    <div className="hero-bar-well">
                      <div className="hero-bar-column bar-dark anim-bar-2" style={{ height: '74%' }}>
                        <span className="hero-bar-val">74%</span>
                      </div>
                    </div>
                    <span className="hero-axis-label">Sowing</span>
                  </div>

                  {/* Bar 3: Growth (Highlighted Lime Bar) */}
                  <div className="hero-chart-bar-group bar-growth-active">
                    <div className="hero-bar-well">
                      <div className="hero-bar-column bar-lime anim-bar-3" style={{ height: '94%' }}>
                        {/* High-tech Glowing Ring Marker */}
                        <div className="hero-lime-ring-marker" />
                        <span className="hero-bar-val-lime">94%</span>
                      </div>
                    </div>
                    <span className="hero-axis-label label-active">Growth</span>
                  </div>

                  {/* Bar 4: Harvest */}
                  <div className="hero-chart-bar-group">
                    <div className="hero-bar-well">
                      <div className="hero-bar-column bar-dark anim-bar-4" style={{ height: '62%' }}>
                        <span className="hero-bar-val">62%</span>
                      </div>
                    </div>
                    <span className="hero-axis-label">Harvest</span>
                  </div>
                </div>
              </div>

              <div className="hero-card-impact-footer">
                <div className="hero-legend-indicator">
                  <span className="hero-legend-dot-lime" />
                  <span>Stress-adjusted projection</span>
                </div>
                <button 
                  className="hero-sim-btn" 
                  onClick={(e) => { e.stopPropagation(); onNavigate('scenarios'); }}
                >
                  <span>Simulate</span>
                  <ChevronRight size={13} strokeWidth={2.4} />
                </button>
              </div>
            </article>
          </div>
        </section>
      </main>
    </div>
  )
}
