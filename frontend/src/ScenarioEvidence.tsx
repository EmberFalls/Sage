import type { Assessment } from './types'

const amount = (v: unknown) => new Intl.NumberFormat('en-IN', {style:'currency',currency:'INR',maximumFractionDigits:2}).format(Number(v||0))

export default function ScenarioEvidence({assessment}:{assessment:Assessment|null}) {
  if (!assessment) return null
  const results = [['Baseline',assessment.baseline],['Climate stress',assessment.stress],['Stress + action',assessment.stress_with_action]] as const
  const selected = assessment.stress_with_action || assessment.stress
  return <section className="card evidence-card">
    <div className="section-title"><div><h2>Bank payment and financial resilience</h2><p>Formal payment status and carried liabilities come from the same dated ledger. Every value is simulated.</p></div></div>
    <div className="comparison-grid">
      {results.map(([label,result]) => <div className="input-tile evidence-column" key={label}>
        <h3>{label}</h3>
        {result ? <>
          <div className="source-row"><span>Bank payment status</span><b>{result.formal_repayment_status.replaceAll('_',' ')}</b></div>
          <div className="source-row"><span>Bank paid this season</span><b>{amount(result.formal_paid_inr)}</b></div>
          <div className="source-row"><span>Actual bridge draw</span><b>{amount(result.bridge_draw_inr)}</b></div>
          <div className="source-row"><span>Formal debt after season 3</span><b>{amount(result.debt_cycle[2].formal_balance_end_inr)}</b></div>
          <div className="source-row"><span>Informal debt after season 3</span><b>{amount(result.debt_cycle[2].informal_balance_end_inr)}</b></div>
          <div className="source-row"><span>Action cost over 3 seasons</span><b>{amount(result.three_season_action_cost_inr)}</b></div>
          <p>{result.modeled_sustainability_status.replaceAll('_',' ')}</p>
        </> : <p>{assessment.action_status==='ineligible'?'The selected action is ineligible at this as-of date.':'Select an action to compare its full schedule and future debt.'}</p>}
      </div>)}
    </div>
    <div className="section-title" style={{marginTop:20}}><div><h2>Selected payment schedule</h2><p>{selected.action_id==='none'?'Original synthetic loan schedule':'Hypothetical proposal · requires bank approval'} · sale arrives {selected.sale_date}</p></div></div>
    <div className="table-wrap"><table><thead><tr><th>Installment date</th><th>Scheduled bank due</th><th>Cash before due</th><th>Actual bank payment</th><th>Unpaid due</th></tr></thead><tbody>
      {selected.payments.map((p:any) => <tr key={p.date}><td>{p.date}</td><td>{amount(p.bank_due_inr)}</td><td>{amount(p.cash_before_due_inr)}</td><td>{amount(p.formal_paid_inr)}</td><td>{amount(p.unmet_due_inr)}</td></tr>)}
    </tbody></table></div>
    <p className="microcopy">Repayment estimate: {selected.probability_basis.repaid_paths} of {selected.probability_basis.paths} declared hypothetical paths settle all installments. No empirical calibration is claimed. Informal borrowing is capped by the selected amount and repaid from surplus when available.</p>
    <div className="source-pills">{(assessment as any).action_candidates.map((a:any)=><span className={`tag ${a.eligible?'olive':'neutral'}`} key={a.action_id}>{a.action_id.replaceAll('_',' ')} · {a.eligible?'demo eligible':'ineligible'}</span>)}</div>
  </section>
}
