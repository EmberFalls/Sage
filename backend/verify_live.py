"""Capture repeatable live API evidence; start the API before running this script."""
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from decimal import Decimal
from app.schemas import ScenarioBundle

OUT = Path(__file__).resolve().parents[1] / "demo" / "verification"
OUT.mkdir(parents=True, exist_ok=True)
API = os.environ.get('SAGE_API_URL', 'http://127.0.0.1:8000').rstrip('/')

def call(path, payload=None):
    request = Request(API + path,
                      data=json.dumps(payload).encode() if payload is not None else None,
                      headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=10) as response:
        return json.load(response)

assert call('/health')['demo_seeded']
assert len(call('/api/borrowers')) == 2
created_ids = set()
for name, payload in {
    'baseline': {},
    'heat': {'overrides': {'heatwave_days': 4}},
    'bridge': {'overrides': {'heatwave_days': 4, 'heatwave_growth_stage': 'harvest',
                           'market_price_change_pct': -80, 'assumed_informal_bridge_inr': 150000}},
    'reschedule': {'overrides': {'heatwave_days': 4}, 'action_id': 'reschedule_30d'},
    'split': {'overrides': {'heatwave_days': 4}, 'action_id': 'split_payment'},
}.items():
    bundle = call('/api/scenarios/evaluate', payload)
    created_ids.add(bundle['scenario_id'])
    ScenarioBundle.model_validate(bundle)
    assert call('/api/scenarios/' + bundle['scenario_id']) == bundle
    selected = bundle['stress_with_action'] or bundle['stress']
    loan = call('/api/borrowers/' + bundle['borrower_id'] + '/loan?scenario_id=' + bundle['scenario_id'])
    assert loan['schedule'] == selected['loan_schedule']
    assert bundle['repayment_bridge']['steps'][-1]['running_balance_inr'] == bundle['stress']['cash_pre_due_inr']
    for result in [bundle['baseline'], bundle['stress'], bundle['stress_with_action']]:
        if result:
            assert Decimal(result['three_season_action_cost_inr']) == sum(
                Decimal(row['action_cost_inr']) for row in result['debt_cycle'])
    (OUT / (name + '.json')).write_text(json.dumps(bundle, indent=2), encoding='utf-8')
    print(name, bundle['scenario_id'], 'gap=' + selected['cash_gap_inr'],
          'bank_paid=' + selected['formal_paid_inr'], 'bridge=' + selected['bridge_draw_inr'])

catalog_ids = {row['scenario_id'] for row in call('/api/scenarios?limit=100')['scenarios']}
assert created_ids <= catalog_ids

(OUT / 'scenario-bundle.schema.json').write_text(
    json.dumps(ScenarioBundle.model_json_schema(), indent=2), encoding='utf-8')
(OUT / 'openapi.json').write_text(json.dumps(call('/openapi.json'), indent=2), encoding='utf-8')
print('Live API and snapshot checks passed; schema captured.')
