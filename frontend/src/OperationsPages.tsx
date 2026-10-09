import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { AlertTriangle, ChevronRight, Database, Download, RefreshCw, Search, Sprout, Upload } from 'lucide-react'

const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

type BorrowerValues = Record<string, string>

const borrowerFields: {key:string; label:string; type?:string; step?:string}[] = [
  {key:'alias',label:'Display name'}, {key:'district',label:'District'}, {key:'branch',label:'Branch'},
  {key:'crop',label:'Crop'}, {key:'area_ha',label:'Farm area (ha)',type:'number',step:'0.01'},
  {key:'irrigation_fraction',label:'Irrigated share (0–1)',type:'number',step:'0.01'},
  {key:'sowing_date',label:'Sowing date',type:'date'}, {key:'harvest_date',label:'Expected harvest',type:'date'},
  {key:'loan_principal_inr',label:'Requested loan principal (INR)',type:'number',step:'0.01'},
  {key:'annual_rate',label:'Annual interest rate (0–1)',type:'number',step:'0.001'},
  {key:'disbursed_at',label:'Planned disbursement',type:'date'}, {key:'due_at',label:'Contractual due date',type:'date'},
  {key:'initial_cash_inr',label:'Opening cash (INR)',type:'number',step:'0.01'},
  {key:'input_cost_inr',label:'Crop input cost (INR)',type:'number',step:'0.01'},
  {key:'living_cost_inr',label:'Household cost (INR)',type:'number',step:'0.01'},
  {key:'yield_t_per_ha',label:'Illustrative baseline yield (t/ha)',type:'number',step:'0.01'},
  {key:'price_inr_per_quintal',label:'Assumed crop price (INR/quintal)',type:'number',step:'0.01'},
  {key:'sale_fraction',label:'Marketable share (0–1)',type:'number',step:'0.01'},
]

const blankBorrower: BorrowerValues = {
  alias:'Demo Farmer', district:'Pune', branch:'Pune Rural', crop:'Maize', area_ha:'1.8',
  irrigation_fraction:'0.25', sowing_date:'2026-06-20', harvest_date:'2026-11-01',
  loan_principal_inr:'100000', annual_rate:'0.12', disbursed_at:'2026-06-22', due_at:'2026-11-05',
  initial_cash_inr:'12000', input_cost_inr:'41000', living_cost_inr:'10000', yield_t_per_ha:'3.2',
  price_inr_per_quintal:'2450', sale_fraction:'0.92',
}

const linkedLoanFields=new Set(['loan_principal_inr','annual_rate','disbursed_at','due_at'])

export function BorrowerForm({initial, onSave, onCancel, loanTermsLocked=false}:{initial?:BorrowerValues; onSave:(values:BorrowerValues)=>Promise<void>; onCancel:()=>void; loanTermsLocked?:boolean}) {
  const [values,setValues]=useState<BorrowerValues>(()=>({...blankBorrower,...initial}))
  const [busy,setBusy]=useState(false),[error,setError]=useState('')
  const submit=async(e:FormEvent)=>{e.preventDefault();setBusy(true);setError('');try{await onSave(values)}catch(err:any){setError(err.message||'Could not save the synthetic borrower')}finally{setBusy(false)}}
  return <form onSubmit={submit}>
    <div className="notice pale"><Sprout size={17}/><div><b>Demo profile only</b><span> The record is labeled synthetic. Never enter real personal or bank data.</span></div></div>
    {loanTermsLocked&&<div className="notice pale"><AlertTriangle size={16}/><div><b>Linked loan terms are locked.</b><span> Use a reviewed application to create a new demo loan; this edit cannot rewrite the existing contract.</span></div></div>}
    <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(190px,1fr))',gap:12,margin:'16px 0'}}>
      {borrowerFields.map(field=><label key={field.key} className="control-label"><span>{field.label}</span>{field.key==='crop'?<select required value={values.crop} onChange={e=>setValues(v=>({...v,crop:e.target.value}))}><option>Maize</option><option>Wheat</option></select>:<input required type={field.type||'text'} step={field.step} value={values[field.key]||''} disabled={loanTermsLocked&&linkedLoanFields.has(field.key)} onChange={e=>setValues(v=>({...v,[field.key]:e.target.value}))}/>}</label>)}
    </div>
    {error&&<div className="error-banner"><AlertTriangle size={16}/>{error}</div>}
    <div style={{display:'flex',justifyContent:'flex-end',gap:9}}><button type="button" className="btn-outline" onClick={onCancel} disabled={busy}>Cancel</button><button className="btn-primary" disabled={busy}>{busy?'Saving…':'Save demo borrower'}</button></div>
  </form>
}

const nextStatus:Record<string,string>={draft:'assessed',assessed:'referred_to_officer',referred_to_officer:'under_review',under_review:'reviewed'}
const statusLabel:Record<string,string>={draft:'Draft',assessed:'Assessed',referred_to_officer:'Referred to officer',under_review:'Under review',reviewed:'Reviewed',approved_in_demo:'Approved in demo',rejected_in_demo:'Rejected in demo'}

export function ApplicationsPage({borrowers,go,onLoanCreated}:{borrowers:{id:string;alias:string;crop:string}[];go:(page:string,borrowerId?:string)=>void;onLoanCreated:()=>Promise<void>}) {
  const [rows,setRows]=useState<any[]>([]),[assessmentCache,setAssessmentCache]=useState<Record<string,any>>({}),[borrowerId,setBorrowerId]=useState(''),[amount,setAmount]=useState('100000'),[purpose,setPurpose]=useState('Seasonal crop inputs'),[notes,setNotes]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false),[query,setQuery]=useState(''),[statusFilter,setStatusFilter]=useState('all')
  const load=()=>fetch(`${API}/api/applications`).then(r=>{if(!r.ok)throw new Error('Application queue is unavailable');return r.json()}).then(data=>{setRows(data.applications);setError('')}).catch(e=>setError(e.message))
  const visibleRows=useMemo(()=>rows.filter(row=>{
    const matchesStatus=statusFilter==='all'||row.status===statusFilter
    const haystack=[row.application_id,row.borrower_id,row.purpose,row.status,...(row.status_history||[]).map((entry:any)=>entry.rationale)].join(' ').toLowerCase()
    return matchesStatus&&haystack.includes(query.trim().toLowerCase())
  }),[rows,statusFilter,query])
  const exportCsv=()=>{
    const columns=['application_id','borrower_id','requested_amount_inr','purpose','status','created_at','assessment_id','loan_id','review_history']
    const quote=(value:unknown)=>`"${String(value??'').replaceAll('"','""')}"`
    const content=[columns.join(','),...visibleRows.map(row=>[
      row.application_id,row.borrower_id,row.requested_amount_inr,row.purpose,row.status,row.created_at,
      row.assessment_id,row.loan_id,JSON.stringify(row.status_history||[]),
    ].map(quote).join(','))].join('\r\n')
    const url=URL.createObjectURL(new Blob([`\uFEFF${content}`],{type:'text/csv;charset=utf-8'}));const link=document.createElement('a')
    link.href=url;link.download='sage-demo-applications.csv';link.click();URL.revokeObjectURL(url)
  }
  useEffect(()=>{if(borrowers.length&&!borrowerId)setBorrowerId(borrowers[0].id)},[borrowers,borrowerId])
  useEffect(()=>{load()},[])
  const create=async(e:FormEvent)=>{e.preventDefault();setBusy(true);setError('');try{const r=await fetch(`${API}/api/applications`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({borrower_id:borrowerId,requested_amount_inr:amount,purpose,notes})});const body=await r.json();if(!r.ok)throw new Error(body.detail||'Application could not be created');await load()}catch(err:any){setError(err.message)}finally{setBusy(false)}}
  const advance=async(row:any,status:string)=>{const rationale=window.prompt(`Add a demo review note for ${statusLabel[status]}:`);if(!rationale?.trim())return;setError('');try{const r=await fetch(`${API}/api/applications/${encodeURIComponent(row.application_id)}/status`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status,rationale})});const body=await r.json();if(!r.ok)throw new Error(body.detail||'Application transition failed');await load();if(status==='assessed'&&body.assessment_id){const result=await fetch(`${API}/api/scenarios/${encodeURIComponent(body.assessment_id)}`).then(response=>response.json());setAssessmentCache(cache=>({...cache,[body.assessment_id]:result}))}if(status==='approved_in_demo')await onLoanCreated()}catch(err:any){setError(err.message)}}
  return <div className="content-grid"><section className="card wide"><div className="section-title"><div><h2>New demo loan application</h2><p>Create a persistent application linked to an existing synthetic borrower.</p></div><span className="tag amber">Simulation only</span></div>
    {!borrowers.length?<div className="empty">Create a borrower profile before starting an application. <button className="text-button" onClick={()=>go('borrowers')}>Open borrower registry <ChevronRight size={14}/></button></div>:<form onSubmit={create}>
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(190px,1fr))',gap:12}}>
        <label className="control-label"><span>Borrower</span><select required value={borrowerId} onChange={e=>setBorrowerId(e.target.value)}>{borrowers.map(b=><option key={b.id} value={b.id}>{b.alias} · {b.crop} · {b.id}</option>)}</select></label>
        <label className="control-label"><span>Requested amount (INR)</span><input required type="number" min="1" step="0.01" value={amount} onChange={e=>setAmount(e.target.value)}/></label>
        <label className="control-label"><span>Purpose</span><input required minLength={3} maxLength={500} value={purpose} onChange={e=>setPurpose(e.target.value)}/></label>
      </div><label className="control-label" style={{display:'block',marginTop:10}}><span>Review context (optional)</span><textarea maxLength={2000} value={notes} onChange={e=>setNotes(e.target.value)} rows={2}/></label>
      <div style={{display:'flex',justifyContent:'flex-end',marginTop:12}}><button className="btn-primary" disabled={busy||!borrowerId}>{busy?'Saving…':'Save application draft'}</button></div>
    </form>}
  </section>
  <section className="card wide"><div className="section-title"><div><h2>Application review queue</h2><p>Every transition is retained with timestamp and rationale. Decisions are demo-only.</p></div><div style={{display:'flex',gap:8,flexWrap:'wrap'}}><button className="btn-outline" onClick={exportCsv} disabled={!visibleRows.length}><Download size={14}/> Export CSV</button><button className="btn-outline" onClick={load}><RefreshCw size={14}/> Refresh</button></div></div>
    {error&&<div className="error-banner"><AlertTriangle size={16}/>{error}</div>}
    {!rows.length?<div className="empty">No loan applications yet.</div>:<><div className="toolbar"><label className="search"><Search size={16}/><input aria-label="Search applications" placeholder="Search application, borrower, purpose or review note" value={query} onChange={e=>setQuery(e.target.value)}/></label><label className="control-label" style={{maxWidth:230}}><span>Status</span><select value={statusFilter} onChange={e=>setStatusFilter(e.target.value)}><option value="all">All statuses</option>{Object.entries(statusLabel).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label><span className="tag neutral">{visibleRows.length} of {rows.length}</span></div>{visibleRows.length?<div className="table-wrap"><table><thead><tr><th>Application / borrower</th><th>Request</th><th>Status</th><th>Activity</th><th>Next step</th></tr></thead><tbody>{visibleRows.map(row=>{const next=nextStatus[row.status],assessment=assessmentCache[row.assessment_id];return <tr key={row.application_id}><td><b>{row.application_id}</b><small>{row.borrower_id} · {row.purpose}</small></td><td>₹{Number(row.requested_amount_inr).toLocaleString('en-IN')}</td><td><span className={`tag ${row.status.includes('approved')?'green':row.status.includes('rejected')?'neutral':'amber'}`}>{statusLabel[row.status]||row.status}</span></td><td>{row.status_history?.length||0} recorded steps{row.assessment_id&&<small>Assessment {row.assessment_id}</small>}{assessment&&<small>Modeled gap ₹{Number(assessment.stress.cash_gap_inr).toLocaleString('en-IN')} · {Math.round(Number(assessment.stress.repayment_probability_simulated)*100)}% simulated feasibility</small>}{row.loan_id&&<small>Demo loan {row.loan_id}</small>}</td><td>{next?<button className="btn-outline" onClick={()=>advance(row,next)}>{statusLabel[next]}</button>:row.status==='reviewed'?<div style={{display:'flex',gap:6}}><button className="btn-primary" onClick={()=>advance(row,'approved_in_demo')}>Approve in demo</button><button className="btn-outline" onClick={()=>advance(row,'rejected_in_demo')}>Reject</button></div>:row.loan_id?<button className="btn-outline" onClick={()=>go('loans',row.borrower_id)}>View demo loan</button>:<span className="tag neutral">Closed</span>}</td></tr>})}</tbody></table></div>:<div className="empty">No applications match these filters.</div>}</>}
  </section><div className="notice amber"><AlertTriangle size={17}/><div><b>No real lending decision is made.</b><span> Demo approval creates a synthetic local loan record only; it does not contact a bank, sanction funds, or change any real account.</span></div></div></div>
}

export function DataSourcesPage() {
  const [data,setData]=useState<any>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[importBusy,setImportBusy]=useState(false)
  const load=()=>fetch(`${API}/api/data-sources`).then(r=>{if(!r.ok)throw new Error('Source registry unavailable');return r.json()}).then(setData).catch(e=>setError(e.message))
  useEffect(()=>{load()},[])
  const refresh=async()=>{setBusy(true);setError('');try{const r=await fetch(`${API}/api/data-sources/open-meteo/refresh`,{method:'POST'});const body=await r.json();if(!r.ok)throw new Error(body.detail||'Source refresh failed');await load()}catch(e:any){setError(e.message)}finally{setBusy(false)}}
  const importFile=async(file?:File)=>{if(!file)return;setImportBusy(true);setError('');try{if(file.size>5_000_000)throw new Error('Import files must be no larger than 5 MB');const payload=JSON.parse(await file.text());const response=await fetch(`${API}/api/data-sources/import`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const body=await response.json();if(!response.ok)throw new Error(body.detail||'Feature import failed');await load()}catch(e:any){setError(e.message||'Feature import failed')}finally{setImportBusy(false)}}
  return <div className="content-grid"><section className="card wide"><div className="section-title"><div><h2>Source registry and freshness</h2><p>Provider status, spatial limits, attribution, units, hashes and stored response snapshots.</p></div><div style={{display:'flex',gap:8,flexWrap:'wrap'}}><button className="btn-primary" onClick={refresh} disabled={busy}><RefreshCw size={14}/>{busy?'Refreshing…':'Refresh Open-Meteo archive'}</button><label className="btn-outline" style={{display:'inline-flex',alignItems:'center',gap:7,cursor:importBusy?'wait':'pointer'}}><Upload size={14}/>{importBusy?'Validating…':'Import provider JSON'}<input type="file" accept="application/json,.json" disabled={importBusy} onChange={e=>{void importFile(e.target.files?.[0]);e.currentTarget.value=''}} style={{display:'none'}}/></label></div></div>
    <p className="microcopy">Normalized import requires source_id, HTTPS source_url, self-reported attribution/license/version/geography, and observations with numeric value, unit and geography. Dated rows require observed_at; crop-calendar rows instead require static_primary_season and start/end day-of-year values. NDVI/soil also require coordinates; market-price rows require a market; yield rows require a crop and harvest year. Imports remain pending source admission and never feed scoring.</p>
    {error&&<div className="error-banner"><AlertTriangle size={16}/>{error}</div>}{!data?<div className="empty">Loading source registry…</div>:<><div className="table-wrap"><table><thead><tr><th>Source</th><th>Status</th><th>Coverage / units</th><th>Runtime use</th></tr></thead><tbody>{data.sources.map((source:any)=><tr key={source.source_id}><td><b>{source.name}</b><small>{source.url||source.source_id} · {source.attribution||source.latest_snapshot?.attribution||'Attribution pending'} · {source.license||source.latest_snapshot?.license||'Terms not verified'}</small></td><td><span className={`tag ${['cached_snapshot','complete_archive_available','cached_complete_archive'].includes(source.status)?'green':source.status==='unavailable'?'neutral':'amber'}`}>{source.status}</span></td><td>{source.spatial_resolution||source.latest_snapshot?.date_start&&`${source.latest_snapshot.date_start} to ${source.latest_snapshot.date_end}`||'Not verified'}<small>{source.units?JSON.stringify(source.units):source.latest_snapshot?.units?JSON.stringify(source.latest_snapshot.units):source.latest_snapshot?.variables?.join(', ')||source.note}</small></td><td>{source.runtime_assessment_use?'Connected':'Not used by scoring'}</td></tr>)}</tbody></table></div><h3 style={{margin:'18px 0 8px'}}>Recent refresh history</h3>{data.recent_refreshes?.length?<div className="table-wrap"><table><thead><tr><th>Attempted (UTC)</th><th>Source</th><th>Result</th><th>Snapshot / error</th></tr></thead><tbody>{data.recent_refreshes.slice(0,10).map((event:any)=><tr key={event.refresh_id}><td>{event.attempted_at}</td><td>{event.source_id}</td><td><span className="tag amber">{event.status}</span></td><td>{event.snapshot_id||event.error_code||'—'}</td></tr>)}</tbody></table></div>:<div className="empty">No refresh attempts recorded yet.</div>}</>}
  </section><section className="card wide"><div className="section-title"><div><h2>Immutable source snapshots</h2><p>Exact UTF-8 response bytes are retained alongside hash and retrieval metadata.</p></div><span className="tag neutral">{data?.snapshots?.length||0} snapshots</span></div>{data?.snapshots?.length?<div className="table-wrap"><table><thead><tr><th>Snapshot</th><th>Retrieved (UTC)</th><th>Window</th><th>Rows</th><th>SHA-256</th><th>Quality</th></tr></thead><tbody>{data.snapshots.map((snapshot:any)=><tr key={snapshot.snapshot_id}><td><b>{snapshot.source_name}</b><small>{snapshot.retrieval_mode}{snapshot.stale_fallback ? ' · cached fallback' : ''}</small></td><td>{snapshot.retrieved_at}</td><td>{snapshot.date_start} – {snapshot.date_end}</td><td>{snapshot.row_count}</td><td><code>{snapshot.content_sha256.slice(0,20)}…</code></td><td><span className="tag amber">{snapshot.quality_status}</span></td></tr>)}</tbody></table></div>:<div className="empty"><Database size={17}/> No refresh snapshot stored yet. The verified three-row excerpt remains available as an explicitly labeled fallback.</div>}
    <p className="microcopy">{data?.claim_limit} NDVI, soil, market price, and matched yield remain unavailable or unverified. Open-Meteo data is historical grid-cell reanalysis; it is never presented as farm measurement.</p>
  </section></div>
}

export function UnavailablePage({title}:{title:string}) {return <section className="card"><div className="section-title"><div><h2>{title}</h2><p>This route is reserved in the full product navigation.</p></div><span className="tag neutral">Not implemented</span></div><div className="empty">The current demo has no authenticated settings or role-management workflow. This destination is intentionally marked unavailable.</div></section>}
