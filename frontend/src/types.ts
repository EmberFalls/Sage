export type Borrower = {id:string; alias:string; district:string; branch:string; crop:string; area_ha:number; irrigation_fraction:number; due_at:string; synthetic:boolean}
export type Assessment = {
  borrower_id:string; scenario_id:string; input_hash:string; comparison_context_hash:string; engine_version:string; assessment_as_of:string; claim_scope:string;
  scenario_request:{borrower_id:string;as_of:string;action_id:string;overrides:{rainfall_change_pct:number;heatwave_days:number;heatwave_growth_stage:string;market_price_change_pct:number;irrigation_fraction:number|null;assumed_informal_bridge_inr:number}};
  frozen_context:{borrower:Record<string,any>};
  baseline: Record<string, any>; stress: Record<string, any>; stress_with_action: Record<string, any>|null;
  action_status:string; comparison_deltas: Record<string, any>; debt_cycle: Record<string, any>[];
  action_candidates:{action_id:string;eligible:boolean;reason:string}[];
  debt_warnings: Record<string, any>[]; repayment_bridge: Record<string, any>; input_data_status:Record<string,string[]>;
  risk_semantics:string; drivers:string[]; warnings:string[];
}
