# F8 intervention comparison and review

F8 adds an illustrative, versioned action catalog and a shared-assessment comparison API. `f8-interventions-demo-v1` is not sourced lender or government policy; `operational_policy_verified` is false. Every candidate carries its catalog/policy version and assumption/source tags. Crop and sowing options remain visible as unsupported until admitted crop and regional configurations exist.

## Evaluation contract

`POST /api/interventions/evaluate` evaluates the no-action context and bounded single actions and declared pairs through the same F6/F7 assessment service. Candidate-specific cash events are dated. Schedule modifications affect due dates, formal interest, fees, and future modeled debt. The response includes the exact due date and cash gap, the later due-date list, incremental cost, interest and season-three debt, ranked candidate IDs, all ineligible/unsupported/unranked options, and scenario result references. The objective and its weights/tie break are returned with the saved comparison bundle.

Assistance is a hypothetical dated credit limited by an explicitly entered scenario budget and illustrative maximum; the same amount is represented as an outlay/program cost in the comparison objective. Insurance has zero payout unless explicit enrollment precedes the illustrative cutoff, a trigger is declared, and payout timing is valid. Outreach does not change numeric risk. Irrigation requires explicit water access and an effective date before the modeled stress window. No actual hidden liability, award, policy enrollment, water access, crop suitability, or lender approval is inferred.

## Proposal/review API

- `GET /api/interventions/catalog`
- `POST /api/interventions/proposals` with comparison ID, candidate ID, actor, and reason
- `GET /api/interventions/proposals`
- `PATCH /api/interventions/proposals/{id}/review` through `proposed -> under_review -> approved_in_demo|rejected_in_demo`

Every transition records actor, reason, assessment reference, and UTC timestamp. Unsupported, ineligible, and unevaluated candidates cannot be proposed. Approval evaluates the saved candidate request again with approval metadata and persists a new simulated result. It never edits posted loan events or sends a message. The terminal states cannot transition again.

## Integration gates

This implementation provides synthetic fixtures/contracts. Production use still depends on F5 posted-ledger integration and F6 saved evidence. F4/F5 must provide authoritative dated cash effects, F7 must provide admitted later-debt consequences, and F6 must support controlled comparisons. F8 crop/sowing support requires agronomic configuration. Legal, lender, insurance, and assistance policies must be sourced and verified before operational eligibility is presented.
