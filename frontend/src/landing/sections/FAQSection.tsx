import React, { useState } from 'react'
import { SectionHeading } from '../components/SectionHeading'
import { DemoDataBadge } from '../components/DemoDataBadge'
import { ChevronDown, HelpCircle } from 'lucide-react'

export function FAQSection() {
  const [openIndex, setOpenIndex] = useState<number | null>(0)

  const faqs = [
    {
      q: 'How does PhenoCredit assess crop and climate risk without on-field visits?',
      a: 'PhenoCredit integrates regional meteorological reanalysis (temperature, heatwave duration, precipitation anomalies) with physiological crop growth stages. By mapping in-season weather events to specific sensitivity windows (such as flowering pollination), it estimates potential yield reduction and compares expected mandi harvest revenue against contractual bank due dates.',
    },
    {
      q: 'What happens when satellite observations are cloud-obscured or unavailable?',
      a: 'In the current prototype, satellite NDVI and soil moisture feeds are explicitly flagged as "Unavailable" rather than fabricated. The system falls back to meteorological reanalysis and assumed physiological calendars, surfacing the exact provenance status on every report so underwriting officers know which data points are observed versus assumed.',
    },
    {
      q: 'Are the outputs trained-ML predictions or deterministic rule-based models?',
      a: 'The current engine uses deterministic, transparent agronomic response rules and cash-flow arithmetic rather than a black-box machine learning model. This ensures every calculation—from yield impact to due-date shortfalls and intervention fees—is fully auditable, explainable, and reproducible.',
    },
    {
      q: 'How does PhenoCredit integrate with a lender’s Core Banking System (CBS)?',
      a: 'PhenoCredit is architected around lightweight REST/JSON APIs and database-agnostic schemas (SQLite for demo environments, PostgreSQL for enterprise deployments). A lender can ingest standard loan portfolios (principal, interest rate, disbursement date, due date) and retrieve scenario risk scores via automated batch APIs.',
    },
    {
      q: 'Does a risk indicator automatically approve, reject, or restructure a loan?',
      a: 'No. PhenoCredit is strictly a decision-support and scenario-modeling platform. All candidate restructuring proposals (such as +30-day rescheduling or split-installment options) are illustrative simulations intended for review by human credit officers and risk committees.',
    },
    {
      q: 'How is borrower financial data protected?',
      a: 'The demonstration repository operates entirely locally on synthetic borrower profiles and offline fixtures. For institutional pilots, the architecture supports on-premise deployment within the financial institution’s secure VPC or local server infrastructure, preventing sensitive borrower records from leaving the bank’s perimeter.',
    },
    {
      q: 'What is currently implemented in this prototype versus planned for future versions?',
      a: 'Currently implemented: 5-stage climate shock engine, dated cash ledger with due-date cutoff, candidate intervention comparisons, 3-season debt cycle warnings, SHA-256 evaluation context hashes, and exportable JSON/CSV snapshots. Planned for future releases: live Sentinel-2 satellite NDVI ingestion, real-time APMC mandi spot price scraping, and calibrated multi-crop agronomic validation.',
    },
  ]

  const toggle = (idx: number) => {
    setOpenIndex(openIndex === idx ? null : idx)
  }

  return (
    <section className="landing-section faq-section" id="faq">
      <div className="landing-container">
        <SectionHeading
          tag="FREQUENTLY ASKED QUESTIONS"
          title="Clear, Honest Answers About the Platform"
          subtitle="Everything you need to know about our data sources, model logic, governance principles, and integration architecture."
          badge={<DemoDataBadge type="verified" text="Platform Disclosures" />}
        />

        <div className="faq-accordion-list">
          {faqs.map((faq, idx) => {
            const isOpen = openIndex === idx
            return (
              <div className={`faq-item ${isOpen ? 'open' : ''}`} key={idx}>
                <button
                  type="button"
                  className="faq-question-btn"
                  onClick={() => toggle(idx)}
                  aria-expanded={isOpen}
                >
                  <span className="faq-question-text">{faq.q}</span>
                  <div className={`faq-icon-arrow ${isOpen ? 'rotated' : ''}`}>
                    <ChevronDown size={18} />
                  </div>
                </button>

                {isOpen && (
                  <div className="faq-answer-pane">
                    <p className="faq-answer-text">{faq.a}</p>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
