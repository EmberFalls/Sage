"""Financial contract and offline API acceptance checks for gates G0–G4."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from datetime import date
from decimal import Decimal as D

from fastapi.testclient import TestClient
from app.main import app
from app.db import _connect, get_borrower_record, get_scenario, save_scenario
from app.schemas import ScenarioBundle, ScenarioRequest
from app.services.assessment import BORROWERS, _daily_reanalysis, _calendar, _assessment, build_dated_ledger, evaluate_scenario, money


class GateVerification(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous_database = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = f"sqlite:///{Path(self.temp.name) / 'verification.db'}"
        self.client_context = TestClient(app)
        self.client = self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        if self.previous_database is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.previous_database
        self.temp.cleanup()

    def evaluate(self, **overrides):
        return evaluate_scenario(ScenarioRequest(overrides=overrides))

    def assert_ledger(self, result):
        running = D(result["opening_cash_inr"])
        dates = []
        for event in result["cash_by_date"]:
            running += D(event["amount_inr"])
            self.assertEqual(running, D(event["cash_after_inr"]))
            dates.append(event["date"])
        self.assertEqual(dates, sorted(dates))
        self.assertEqual(running, D(result["net_free_cash_inr"]))

    def test_g0_health_seed_and_typed_contract(self):
        self.assertTrue(self.client.get('/health').json()['demo_seeded'])
        for _ in range(2):
            self.assertEqual(self.client.post('/api/demo/seed').json()['borrower_count'], 2)
        result = self.client.post('/api/scenarios/evaluate', json={}).json()
        ScenarioBundle.model_validate(result)
        self.assertEqual(len(result['input_hash']), 64)
        self.assertIn('hypothetical', result['risk_semantics'])

    def test_g1_db_records_sources_and_chronological_loan(self):
        for borrower in self.client.get('/api/borrowers').json():
            row = self.client.get(f"/api/borrowers/{borrower['id']}").json()
            self.assertTrue(row['synthetic'])
            loan = self.client.get(f"/api/borrowers/{borrower['id']}/loan").json()
            self.assertEqual([e['date'] for e in loan['events']], sorted(e['date'] for e in loan['events']))
            self.assertTrue(all(e['amount_inr'] != 'pending_scenario_calculation' for e in loan['events']))
        self.assertEqual(self.client.get('/api/sources').status_code, 200)
        self.assertIsNone(self.client.get('/api/climate').json()['weather']['forecast_issued_at'])

    def test_g2_all_inputs_and_honest_missing_status(self):
        result = self.evaluate()['stress']
        self.assertEqual(set(result['fin03_inputs']), {'satellite','weather_forecast','soil','crop','irrigation','yield_history','market_price','credit_history'})
        self.assertIsNone(result['fin03_inputs']['satellite']['value'])
        self.assertFalse(result['fin03_inputs']['credit_history']['observed_bank_data'])
        self.assertEqual(len(result['crop_stages']), 5)
        basis = result['probability_basis']
        self.assertEqual(D(result['repayment_probability_simulated']), (D(basis['repaid_paths'])/basis['paths']).quantize(D('.0001')))

    def test_g2_interest_uses_actual_days(self):
        b = BORROWERS['B-DEMO-001']
        expected = money(b['loan_principal_inr'] * (1+b['annual_rate']*D((b['due_at']-b['disbursed_at']).days)/365))
        self.assertEqual(D(self.evaluate()['baseline']['contractual_due_inr']), expected)

    def test_g2_ledger_and_revenue_units(self):
        result = self.evaluate(heatwave_days=1, market_price_change_pct=-12)['stress']
        self.assert_ledger(result)
        b = BORROWERS['B-DEMO-001']
        expected = money(D(result['production_tonnes'])*10*D(result['price_inr_per_quintal'])*b['sale_fraction'])
        self.assertEqual(D(result['gross_revenue_inr']), expected)

    def test_g3_stage_changes_features_yield_and_event_dates(self):
        flowering = self.evaluate(heatwave_days=4, heatwave_growth_stage='flowering')
        planting = self.evaluate(heatwave_days=4, heatwave_growth_stage='planting')
        self.assertEqual(flowering['baseline']['gross_revenue_inr'], planting['baseline']['gross_revenue_inr'])
        self.assertLess(D(flowering['stress']['yield_t_per_ha']), D(planting['stress']['yield_t_per_ha']))
        self.assertNotEqual(flowering['stress']['heat_event']['start_date'], planting['stress']['heat_event']['start_date'])
        self.assertNotEqual(flowering['stress']['stage_stress'], planting['stress']['stage_stress'])

    def test_stage_calendar_provenance_and_weather_cutoff(self):
        b = dict(BORROWERS['B-DEMO-002'])
        b['sowing_date'], b['harvest_date'] = date(2015, 6, 1), date(2015, 10, 31)
        stages = _calendar(b)
        self.assertTrue(all(date.fromisoformat(x['start_date']) >= b['sowing_date'] and date.fromisoformat(x['end_date']) <= b['harvest_date'] for x in stages))
        self.assertTrue(all(x['source'] and x['method'] and x['uncertainty'] and x['geography'] and x['version'] for x in stages))
        self.assertTrue(all(date.fromisoformat(a['end_date']) < date.fromisoformat(c['start_date']) for a,c in zip(stages,stages[1:])))
        weather = _daily_reanalysis(b, stages, date(2015, 8, 1))
        self.assertEqual(weather['source_class'], 'reanalysis')
        self.assertEqual(weather['timezone'], 'Asia/Kolkata')
        self.assertTrue(weather['future_observations_excluded'])
        self.assertEqual(weather['availability_lag_days'], 5)
        self.assertTrue(all(not x.get('date_end') or x['date_end'] <= date(2015, 7, 27).isoformat() for x in weather['stages'].values()))

    def test_observed_reanalysis_changes_stage_response_and_yield(self):
        b = dict(BORROWERS['B-DEMO-002'])
        b['sowing_date'], b['harvest_date'] = date(2015, 6, 1), date(2015, 10, 31)
        request = ScenarioRequest(as_of=date(2015, 12, 1))
        original = _assessment(b, request, shock=False)
        shifted = dict(b, sowing_date=date(2015, 6, 11))
        moved = _assessment(shifted, request, shock=False)
        self.assertEqual(original['reanalysis']['status'], 'available')
        self.assertNotEqual(original['stage_weather_features'], moved['stage_weather_features'])
        self.assertNotEqual(original['stage_stress'], moved['stage_stress'])
        self.assertNotEqual(original['yield_t_per_ha'], moved['yield_t_per_ha'])
        self.assertEqual(original['yield_projection']['source_class'], 'illustrative_rule')
        self.assertIn('not_trained_or_calibrated', original['yield_projection']['status'])

    def test_short_season_stages_are_unavailable_instead_of_overlapping(self):
        b = dict(BORROWERS['B-DEMO-002'])
        b['sowing_date'], b['harvest_date'] = date(2026, 6, 1), date(2026, 6, 3)
        stages = _calendar(b)
        active = [row for row in stages if row['start_date']]
        self.assertEqual(len(active), 3)
        self.assertEqual(len({row['start_date'] for row in active}), 3)
        self.assertEqual([row['name'] for row in stages if not row['start_date']], ['grain_fill', 'harvest'])
        weather = _daily_reanalysis(b, stages, date(2026, 6, 30))
        self.assertEqual(weather['stages']['grain_fill']['status'], 'unavailable_short_season')

    def test_api_baseline_and_calendar_date_shift_are_reproducible(self):
        base = {'as_of':'2026-10-09','overrides':{'heatwave_days':4,'heatwave_growth_stage':'flowering'}}
        baseline = self.client.post('/api/scenarios/evaluate', json=base).json()
        shifted_req = {'as_of':'2026-10-09','overrides':{'heatwave_days':4,'heatwave_growth_stage':'flowering','heatwave_start_date':'2026-07-01'}}
        shifted = self.client.post('/api/scenarios/evaluate', json=shifted_req).json()
        self.assertEqual(baseline['stress']['heat_event']['stage'], 'flowering')
        self.assertEqual(shifted['stress']['heat_event']['stage'], 'planting')
        self.assertEqual(baseline['stress']['reanalysis']['status'], 'missing_geography_mismatch')
        self.assertEqual(baseline['stress']['fin03_inputs']['weather_forecast']['status'], 'hypothetical_scenario')
        self.assertEqual(baseline['stress']['fin03_inputs']['weather_forecast']['operational_forecast']['status'], 'unavailable')
        self.assertNotEqual(baseline['stress']['stage_stress'], shifted['stress']['stage_stress'])
        self.assertNotEqual(baseline['stress']['yield_t_per_ha'], shifted['stress']['yield_t_per_ha'])
        self.assertEqual(baseline, self.client.post('/api/scenarios/evaluate', json=base).json())
        projection = shifted['stress']['yield_projection']
        self.assertEqual(projection['source_class'], 'illustrative_rule')
        self.assertEqual(projection['unit'], 't/ha')
        self.assertIn('not_trained_or_calibrated', projection['status'])
        self.assertEqual(self.client.get('/api/crop-calendar').status_code, 200)

    def test_g3_post_due_sale_excluded_and_price_changes_bridge(self):
        stressed = self.evaluate(heatwave_days=4)
        first_due = stressed['stress']['due_date']
        self.assertGreater(stressed['stress']['sale_date'], first_due)
        self.assertGreater(D(stressed['stress']['cash_gap_inr']), 0)
        self.assertEqual(D(stressed['baseline']['cash_gap_inr']), 0)
        price = self.evaluate(market_price_change_pct=-20)
        self.assertNotEqual(price['repayment_bridge']['steps'], self.evaluate()['repayment_bridge']['steps'])

    def test_g3_bridge_reconciles_at_paise(self):
        for heat, price in [(0,0),(1,-12),(4,-20),(14,-70)]:
            bundle = self.evaluate(heatwave_days=heat, market_price_change_pct=price)
            bridge = bundle['repayment_bridge']
            self.assertEqual(sum(D(s['amount_inr']) for s in bridge['steps']), D(bridge['cash_pre_due_inr']))
            self.assertEqual(D(bridge['shortfall_inr']), max(D('0'), D(bridge['due_inr'])-max(D('0'),D(bridge['cash_pre_due_inr']))))

    def test_g3_reset_reproducibility_and_frozen_baseline(self):
        baseline = self.evaluate()
        stressed = self.evaluate(heatwave_days=8, rainfall_change_pct=-25, assumed_informal_bridge_inr=60000)
        self.assertEqual(baseline['baseline'], {**stressed['baseline'], 'comparison_context_hash': baseline['comparison_context_hash']})
        self.assertEqual(baseline, self.evaluate())

    def test_g4_bridge_can_pay_bank_without_erasing_liability(self):
        no_bridge = self.evaluate(heatwave_days=14, market_price_change_pct=-70)
        with_bridge = self.evaluate(heatwave_days=14, market_price_change_pct=-70, assumed_informal_bridge_inr=150000)
        self.assertGreater(D(no_bridge['stress']['formal_balance_end_inr']), 0)
        self.assertEqual(D(with_bridge['stress']['formal_balance_end_inr']), 0)
        self.assertGreater(D(with_bridge['stress']['informal_balance_end_inr']), 0)
        self.assertIn('BRIDGE_USED_FOR_FORMAL_DUE', [w['id'] for w in with_bridge['debt_warnings']])
        self.assertNotIn('BRIDGE_USED_FOR_FORMAL_DUE', [w['id'] for w in no_bridge['debt_warnings']])
        self.assertGreater(D(with_bridge['debt_cycle'][-1]['informal_balance_end_inr']), D(with_bridge['debt_cycle'][0]['informal_balance_end_inr']))
        self.assertTrue(all(w['simulation_only'] for w in with_bridge['debt_warnings']))

    def test_g4_paid_principal_is_not_readded(self):
        b = BORROWERS['B-DEMO-001']
        flow = build_dated_ledger(b, D('100000'), date(2026,11,1), [{'date':date(2026,11,5),'amount_inr':D('120000')}], D('0'))
        self.assertEqual(flow['formal_balance_end_inr'], 0)
        self.assertEqual(flow['bridge_draw_inr'], 0)
        self.assert_ledger(flow)

    def test_g4_both_actions_same_shock_and_full_schedule(self):
        request = {'overrides':{'heatwave_days':4}}
        stress = self.client.post('/api/scenarios/evaluate',json=request).json()
        candidates = self.client.post('/api/interventions/evaluate',json=request).json()['candidates']
        self.assertEqual(len(candidates),2)
        for bundle in candidates:
            action = bundle['stress_with_action']
            self.assertEqual(bundle['comparison_context_hash'],stress['comparison_context_hash'])
            self.assertEqual(action['gross_revenue_inr'],bundle['stress']['gross_revenue_inr'])
            self.assertLess(D(action['cash_gap_inr']), D(bundle['stress']['cash_gap_inr']))
            self.assert_ledger(action)
            self.assertEqual(len(action['debt_cycle']),3)
            self.assertEqual(D(action['bank_total_due_inr']), D(action['contractual_due_inr'])+D(action['action_cost_inr']))
        split = candidates[1]['stress_with_action']
        self.assertEqual(len(split['payments']),2)
        self.assertNotEqual(candidates[0]['stress_with_action']['bank_total_due_inr'],split['bank_total_due_inr'])

    def test_g4_ineligible_action_has_no_result(self):
        bundle = self.client.post('/api/scenarios/evaluate',json={'as_of':'2026-11-06','action_id':'reschedule_30d'}).json()
        self.assertEqual(bundle['action_status'],'ineligible')
        self.assertIsNone(bundle['stress_with_action'])

    def test_saved_reopen_and_loan_use_same_selected_snapshot(self):
        bundle = self.client.post('/api/scenarios/evaluate',json={'overrides':{'heatwave_days':4},'action_id':'split_payment'}).json()
        self.assertEqual(self.client.get(f"/api/scenarios/{bundle['scenario_id']}").json(), bundle)
        loan = self.client.get(f"/api/borrowers/{bundle['borrower_id']}/loan?scenario_id={bundle['scenario_id']}").json()
        self.assertEqual(loan['computed_due_gap_inr'],bundle['stress_with_action']['cash_gap_inr'])
        self.assertEqual(loan['schedule'],bundle['stress_with_action']['loan_schedule'])

    def test_g5_saved_snapshot_catalog_and_reopen_request(self):
        bundle = self.client.post('/api/scenarios/evaluate',json={
            'overrides': {'heatwave_days': 4, 'market_price_change_pct': -20},
            'action_id': 'split_payment'}).json()
        catalog = self.client.get('/api/scenarios?limit=10').json()['scenarios']
        row = next(item for item in catalog if item['scenario_id'] == bundle['scenario_id'])
        self.assertEqual(row['input_hash'], bundle['input_hash'])
        reopened = self.client.get(f"/api/scenarios/{bundle['scenario_id']}").json()
        self.assertEqual(reopened['scenario_request']['overrides']['heatwave_days'], 4)
        self.assertEqual(reopened['scenario_request']['action_id'], 'split_payment')
        self.assertEqual(reopened, bundle)

    def test_g5_older_immutable_snapshot_reopens_from_saved_request(self):
        bundle = self.client.post('/api/scenarios/evaluate',json={
            'overrides': {'heatwave_days': 3}, 'action_id': 'reschedule_30d'}).json()
        legacy = dict(bundle)
        legacy.pop('scenario_request')
        save_scenario('legacy-snapshot-fixture', bundle['borrower_id'], bundle['input_hash'],
                      {'borrower_id': bundle['borrower_id'], 'action_id': 'reschedule_30d',
                       'overrides': {'heatwave_days': 3}}, legacy)
        self.assertEqual(get_scenario('legacy-snapshot-fixture')['scenario_request']['action_id'], 'reschedule_30d')
        restored = get_scenario('legacy-snapshot-fixture')['scenario_request']
        self.assertEqual(restored['as_of'], '2026-10-09')
        self.assertEqual(restored['overrides']['rainfall_change_pct'], 0)
        self.assertIsNone(restored['overrides']['irrigation_fraction'])

    def test_g5_snapshot_freezes_custom_context_when_borrower_changes(self):
        request = {'as_of': '2026-11-06', 'overrides': {'irrigation_fraction': 0.8,
                   'heatwave_days': 4}, 'action_id': 'split_payment'}
        saved = self.client.post('/api/scenarios/evaluate', json=request).json()
        profile = get_borrower_record(saved['borrower_id'])
        profile['area_ha'] = 9
        with _connect() as con:
            con.execute('UPDATE borrowers SET record_json=? WHERE borrower_id=?',
                        (json.dumps(profile), saved['borrower_id']))
        fresh = self.client.post('/api/scenarios/evaluate', json=request).json()
        self.assertNotEqual(fresh['input_hash'], saved['input_hash'])
        reopened = self.client.get('/api/scenarios/' + saved['scenario_id']).json()
        self.assertEqual({k:v for k,v in reopened.items() if k not in {'snapshot_freshness','snapshot_stale_reasons'}},
                         {k:v for k,v in saved.items() if k not in {'snapshot_freshness','snapshot_stale_reasons'}})
        self.assertEqual(reopened['snapshot_freshness'], 'stale')
        self.assertIn('borrower_profile_changed', reopened['snapshot_stale_reasons'])
        self.assertEqual(reopened['scenario_request']['as_of'], '2026-11-06')
        self.assertEqual(reopened['scenario_request']['overrides']['irrigation_fraction'], 0.8)
        self.assertEqual(reopened['action_status'], 'ineligible')

    def test_invalid_requests_fail_with_typed_errors(self):
        for payload in [{'overrides':{'heatwave_days':-1}}, {'overrides':{'heatwave_growth_stage':'fake'}}, {'as_of':'not-a-date'}, {'overrides':{'irrigation_fraction':1.5}}]:
            self.assertEqual(self.client.post('/api/scenarios/evaluate',json=payload).status_code,422)
        self.assertEqual(self.client.post('/api/scenarios/evaluate',json={'borrower_id':'missing'}).status_code,404)


if __name__ == '__main__':
    unittest.main(verbosity=2)
