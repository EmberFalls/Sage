import React from 'react'
import { SectionHeading } from '../components/SectionHeading'
import { DemoDataBadge } from '../components/DemoDataBadge'
import { Check, X, Minus, HelpCircle } from 'lucide-react'

export function ComparisonMatrix() {
  const comparisonRows = [
    {
      capability: 'Crop-stage-aware climate vulnerability',
      traditional: 'Not typically captured',
      weather: 'Raw weather totals only',
      phenocredit: '5-stage physiological sensitivity weighting',
      phenoStatus: true,
      tradStatus: false,
      weathStatus: 'partial',
    },
    {
      capability: 'Dated bank due vs harvest revenue timing',
      traditional: 'Fixed schedule check',
      weather: 'Not applicable',
      phenocredit: 'Chronological cash ledger pre-due cutoff',
      phenoStatus: true,
      tradStatus: false,
      weathStatus: false,
    },
    {
      capability: 'Pre-delinquency restructuring proposals',
      traditional: 'Post-default remediation only',
      weather: 'Not applicable',
      phenocredit: 'Simulated +30d reschedule and split-payment trade-offs',
      phenoStatus: true,
      tradStatus: false,
      weathStatus: false,
    },
    {
      capability: 'Multi-season informal debt cycle tracking',
      traditional: 'Formal loan ledger only',
      weather: 'Not applicable',
      phenocredit: '3-season informal bridge borrowing simulation',
      phenoStatus: true,
      tradStatus: false,
      weathStatus: false,
    },
    {
      capability: 'Input provenance transparency',
      traditional: 'Proprietary score formula',
      weather: 'Forecast issue stamps',
      phenocredit: 'Explicit tracking of verified, assumed & synthetic fields',
      phenoStatus: true,
      tradStatus: 'partial',
      weathStatus: 'partial',
    },
    {
      capability: 'Deterministic context hash for compliance',
      traditional: 'Variable by bureau version',
      weather: 'Not applicable',
      phenocredit: 'SHA-256 evaluation hash linking inputs to outputs',
      phenoStatus: true,
      tradStatus: false,
      weathStatus: false,
    },
  ]

  return (
    <section className="landing-section comparison-section" id="comparison">
      <div className="landing-container">
        <SectionHeading
          tag="CAPABILITY COMPARISON"
          title="How PhenoCredit expands agricultural underwriting"
          subtitle="A precise look at how in-season phenology context and dated cash modeling compare against generic credit bureaus and standalone weather applications."
          badge={<DemoDataBadge type="verified" text="Feature Matrix" />}
        />

        <div className="comparison-table-wrapper">
          <table className="comparison-table" aria-label="PhenoCredit Capability Comparison">
            <thead>
              <tr>
                <th className="th-feature">Assessment Capability</th>
                <th className="th-trad">Traditional Credit Bureau</th>
                <th className="th-weather">Standalone Weather App</th>
                <th className="th-pheno">
                  <div className="pheno-header-pill">
                    <span>PhenoCredit (FIN-03)</span>
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              {comparisonRows.map((row, idx) => (
                <tr key={idx}>
                  <td className="td-feature">
                    <b>{row.capability}</b>
                  </td>

                  <td className="td-trad">
                    <div className="td-cell-content">
                      {row.tradStatus === false ? (
                        <X size={15} className="text-red-400 flex-shrink-0" />
                      ) : (
                        <Minus size={15} className="text-gray-400 flex-shrink-0" />
                      )}
                      <span>{row.traditional}</span>
                    </div>
                  </td>

                  <td className="td-weather">
                    <div className="td-cell-content">
                      {row.weathStatus === false ? (
                        <X size={15} className="text-red-400 flex-shrink-0" />
                      ) : (
                        <Minus size={15} className="text-amber-500 flex-shrink-0" />
                      )}
                      <span>{row.weather}</span>
                    </div>
                  </td>

                  <td className="td-pheno highlight-cell">
                    <div className="td-cell-content">
                      <Check size={16} className="text-lime-500 flex-shrink-0" />
                      <strong>{row.phenocredit}</strong>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
