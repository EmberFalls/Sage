import type { Assessment } from './types'

const amount = (v: unknown) => new Intl.NumberFormat('en-IN', {style:'currency',currency:'INR',maximumFractionDigits:2}).format(Number(v||0))

export default function ScenarioEvidence({assessment}:{assessment:Assessment|null}) {
  if (!assessment) return null
  const results = [['Baseline',assessment.baseline],['Climate stress',assessment.stress],['Stress + action',assessment.stress_with_action]] as const
  const selected = assessment.stress_with_action || assessment.stress
  const worlds = (assessment as any).debt_worlds || {}
  const fmt = (v:unknown) => amount(v)
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
    <div className="section-title" style={{marginTop:20}}><div><h2>Three season debt timeline</h2><p>The same frozen climate and price shock repeats in all three bridge seasons. Both worlds start from the same opening context; bridge draws remain modeled assumptions.</p></div></div>
    {(['no_bridge','bridge'] as const).map(worldKey => { const world=worlds[worldKey]; return world ? <div key={worldKey} style={{marginBottom:18}}>
      <h3>{world.label}</h3>
      <div className="table-wrap"><table><thead><tr><th>Season dates</th><th>Opening / closing cash</th><th>Formal principal open → close</th><th>Formal interest accrued / capitalized</th><th>Unpaid due</th><th>Informal open + draw → close</th><th>Total debt close</th></tr></thead><tbody>
        {world.seasons.map((s:any)=><tr key={s.season_id}><td>{s.season_id}<small>{s.season_start_date} – {s.season_end_date}</small></td><td>{fmt(s.opening_cash_inr)}<small>→ {fmt(s.closing_cash_inr)}</small></td><td>{fmt(s.opening_formal_principal_inr)}<small>+ {fmt(s.new_formal_principal_inr)} – {fmt(s.principal_paid_inr)} → {fmt(s.formal_principal_end_inr)}</small></td><td>{fmt(s.formal_interest_accrued_inr)}<small>capitalized {fmt(s.formal_interest_capitalized_inr)}; paid {fmt(s.formal_interest_paid_inr)}</small></td><td>{fmt(s.unmet_due_inr)}<small>{s.unpaid_obligations.length} modeled obligation(s)</small></td><td>{fmt(s.opening_informal_principal_inr)} + {fmt(s.informal_draw_inr)}<small>interest {fmt(s.informal_interest_accrued_inr)}; capitalized {fmt(s.informal_interest_capitalized_inr)}; paid {fmt(s.informal_interest_paid_inr)} → {fmt(s.informal_balance_end_inr)}</small></td><td>{fmt(s.total_debt_end_inr)}</td></tr>)}
      </tbody></table></div>
      <details><summary>View dated ledger events and bridge terms</summary>{world.seasons.map((s:any)=><div key={s.season_id}><b>{s.season_id}</b><div className="table-wrap"><table><thead><tr><th>Date</th><th>Event</th><th>Amount</th><th>Event ID / terms</th></tr></thead><tbody>{s.cash_by_date.map((e:any,i:number)=><tr key={`${s.season_id}-${i}`}><td>{e.date}</td><td>{e.kind}</td><td>{fmt(e.amount_inr)}</td><td>{e.event_id}</td></tr>)}{s.payments.map((p:any)=><tr key={p.event_id}><td>{p.date}</td><td>Formal due and payment</td><td>{fmt(p.bank_due_inr)}</td><td><code>{p.event_id}</code><small>paid {fmt(p.formal_paid_inr)} · unpaid {fmt(p.unmet_due_inr)} · principal {fmt(p.principal_paid_inr)} · interest {fmt(p.interest_paid_inr)}</small></td></tr>)}{s.bridge_events.map((e:any)=><tr key={e.event_id}><td>{e.effective_date}</td><td>Modeled informal bridge draw · {e.source_tag}</td><td>{fmt(e.amount_inr)}</td><td><code>{e.event_id}</code><small>limit {fmt(e.limit_inr)} · {Number(e.annual_rate)*100}% assumed · repay {e.repayment_date}</small></td></tr>)}</tbody></table></div></div>)}</details>
    </div> : null })}
    <p className="microcopy">This is an explicitly synthetic scenario. It does not assert that a borrower has undisclosed liabilities. Formal payment status is a ledger result; sustainable repayment is assessed separately from total carried debt and future cash.</p>
  </section>
}
