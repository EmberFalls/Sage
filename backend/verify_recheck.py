"""Live regression evidence for complete saved context and the snapshot catalog."""
import json
from pathlib import Path
from urllib.request import Request, urlopen

request = {'borrower_id': 'B-DEMO-001', 'as_of': '2026-11-06',
           'overrides': {'irrigation_fraction': 0.8, 'heatwave_days': 4,
                         'rainfall_change_pct': -20}, 'action_id': 'split_payment'}
base = 'http://127.0.0.1:8000'
def call(path, data=None):
    with urlopen(Request(base + path, data=json.dumps(data).encode() if data else None,
                         headers={'Content-Type': 'application/json'}), timeout=10) as response:
        return json.load(response)

bundle = call('/api/scenarios/evaluate', request)
assert bundle['action_status'] == 'ineligible'
reopened = call('/api/scenarios/' + bundle['scenario_id'])
assert reopened == bundle
assert reopened['scenario_request']['as_of'] == '2026-11-06'
assert reopened['scenario_request']['overrides']['irrigation_fraction'] == 0.8
assert bundle['scenario_id'] in {v['scenario_id'] for v in call('/api/scenarios?limit=100')['scenarios']}
out = Path(__file__).resolve().parents[1] / 'demo' / 'verification'
(out / 'recheck-snapshot.json').write_text(json.dumps(bundle, indent=2), encoding='utf-8')
print('Custom context snapshot:', bundle['scenario_id'], 'as_of=2026-11-06 irrigation=0.8 action=ineligible')
