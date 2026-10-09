import React from 'react'
import { HeroSection } from '../HeroSection'
import { CapabilityTicker } from './sections/CapabilityTicker'
import { BentoGrid } from './sections/BentoGrid'
import { InteractiveFeatures } from './sections/InteractiveFeatures'
import { ClimateStressSimulator } from './sections/ClimateStressSimulator'
import { DataPipeline } from './sections/DataPipeline'
import { ComparisonMatrix } from './sections/ComparisonMatrix'
import { BorrowerCaseStudy } from './sections/BorrowerCaseStudy'
import { TrustSection } from './sections/TrustSection'
import { FAQSection } from './sections/FAQSection'
import { LandingFooter } from './sections/LandingFooter'

interface LandingPageProps {
  onNavigate: (page: string) => void
}

export function LandingPage({ onNavigate }: LandingPageProps) {
  return (
    <div className="landing-page-root">
      {/* 1. Hero Section (Preserved Original Implementation) */}
      <HeroSection onNavigate={onNavigate} />

      {/* 2. Platform Capability Ticker */}
      <CapabilityTicker />

      {/* 3. Problem vs Solution Bento Grid */}
      <BentoGrid onNavigate={onNavigate} />

      {/* 4. Interactive Product Walkthrough */}
      <InteractiveFeatures onNavigate={onNavigate} />

      {/* 5. Climate Stress Simulator (Signature Hands-On Section) */}
      <ClimateStressSimulator onNavigate={onNavigate} />

      {/* 6. Data Pipeline & Model Architecture */}
      <DataPipeline />

      {/* 7. Comparative Advantage Matrix */}
      <ComparisonMatrix />

      {/* 8. Synthetic Borrower Case Study */}
      <BorrowerCaseStudy onNavigate={onNavigate} />

      {/* 9. Deployment, Governance & Trust */}
      <TrustSection />

      {/* 10. FAQ Accordion */}
      <FAQSection />

      {/* 11. Conversion Glassmorphic Footer */}
      <LandingFooter onNavigate={onNavigate} />
    </div>
  )
}
