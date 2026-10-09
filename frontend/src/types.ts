export type CashLedgerEvent={event_id:string;effective_date:string;category:string;direction:'credit'|'debit';amount_inr:string;principal_component_inr:string|null;interest_component_inr:string|null;running_cash_inr:string;data_status:string;scenario_only:boolean;note:string}
export type Borrower = {id:string; alias:string; district:string; branch:string; crop:string; area_ha:number; irrigation_fraction:number; due_at:string; synthetic:boolean}
export type Assessment = {
  snapshot_freshness?:'current'|'stale'|null; snapshot_stale_reasons?:string[];
  created_at?:string; result_hash?:string; supersedes_id?:string; comparison_bundle_id?:string;
  borrower_id:string; scenario_id:string; input_hash:string; comparison_context_hash:string; engine_version:string; assessment_as_of:string; claim_scope:string;
  scenario_request:{borrower_id:string;as_of:string;action_id:string;loan_principal_override_inr?:number|string|null;overrides:{rainfall_change_pct:number;heatwave_days:number;heatwave_growth_stage:string;heatwave_start_date?:string|null;market_price_change_pct:number;irrigation_fraction:number|null;assumed_informal_bridge_inr:number}};
  frozen_context:{borrower:Record<string,any>};
  baseline: Record<string, any>; stress: Record<string, any>; stress_with_action: Record<string, any>|null;
  action_status:string; comparison_deltas: Record<string, any>; debt_cycle: Record<string, any>[];
  action_candidates:{action_id:string;eligible:boolean;reason:string}[];
  debt_warnings: Record<string, any>[]; repayment_bridge: Record<string, any>; input_data_status:Record<string,string[]>;
  risk_semantics:string; drivers:string[]; warnings:string[];
  // F5 additive fields
  cash_ledger?: {events: CashLedgerEvent[]; opening_cash_inr:string; closing_cash_inr:string; expected_closing_cash_inr:string; reconciled_to_paise:boolean; rounding_policy:string; minimum_reserve_policy:string; unpaid_obligations:{obligation_id:string;effective_date:string;category:string;amount_inr:string;scenario_only:boolean;source_ids:string[]}[]; limitations:string[]};
  credit_history_summary?: {events_as_of:Record<string,any>[]; total_scheduled_payments:number; total_actual_payments:number; overdue_event_count:number; max_days_overdue:number; arrears_detected:boolean; renewal_or_rollover_count:number; utilization_fraction:string|null; data_provenance:string; observed_bank_data:boolean; history_completeness:string; limitations:string[]};
  feasibility_detail?: {deterministic_result:string; cash_gap_inr:string; cash_gap_total_all_dues_inr:string; payments_with_gap:number; total_payments:number; simulated_repayment_rate:string; simulated_shortfall_rate:string; simulation_scope:Record<string,any>; formal_balance_end_inr:string; formal_repayment_status:string; revenue_before_due:string; contractual_due:string; minimum_reserve_inr:string; same_day_ordering_policy?:string; revenue_after_due_policy?:string; limitations:string[]};
  f5_ledger_version?: string;
}
