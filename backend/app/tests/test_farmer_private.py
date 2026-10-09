"""Private farmer access, projection, request, report and audit regressions."""
import os
import csv
import io
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.db import _connect
from app.auth.service import create_user
from app.main import app


class FarmerPrivateVerification(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f"sqlite:///{Path(self.temp.name) / 'farmer.db'}"
        self.context = TestClient(app)
        self.client = self.context.__enter__()

    def tearDown(self):
        self.context.__exit__(None, None, None)
        if self.previous is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = self.previous
        self.temp.cleanup()

    def login_farmer(self, phone):
        code = self.client.post('/api/auth/otp/send', json={'phone':phone}).json()['otp']
        response = self.client.post('/api/auth/otp/verify', json={'phone':phone, 'otp':code})
        self.assertEqual(response.status_code, 200)
        return {'Authorization':'Bearer ' + response.json()['access_token']}

    def test_private_projection_hides_other_farmer_and_sensitive_fields(self):
        a = self.login_farmer('9876543210')
        b = self.login_farmer('9876543211')
        result = self.client.post('/api/scenarios/evaluate', json={'borrower_id':'B-DEMO-001'}).json()
        own = self.client.get('/api/private/farmer/assessments/' + result['scenario_id'], headers=a)
        self.assertEqual(own.status_code, 200)
        self.assertEqual(own.json()['assessment']['cash_gap_inr'], result['stress']['cash_gap_inr'])
        self.assertNotIn('credit_history', own.text)
        self.assertNotIn('scenario_request', own.text)
        self.assertEqual(self.client.get('/api/private/farmer/assessments/' + result['scenario_id'], headers=b).status_code, 404)
        self.assertEqual(self.client.get('/api/private/farmer/assessments/not-a-real-id', headers=a).status_code, 404)
        self.assertEqual(self.client.get('/api/private/farmer/home').status_code, 401)

    def test_request_is_persistent_and_reports_match_saved_result(self):
        headers = self.login_farmer('9876543210')
        result = self.client.post('/api/scenarios/evaluate', json={'borrower_id':'B-DEMO-001'}).json()
        created = self.client.post('/api/private/farmer/requests', headers=headers,
                                   json={'assessment_id':result['scenario_id'], 'message':'Please explain my due date.'})
        self.assertEqual(created.status_code, 201)
        request_id = created.json()['request_id']
        self.assertEqual(self.client.get('/api/private/farmer/requests', headers=headers).json()['requests'][0]['request_id'], request_id)
        self.assertEqual(self.client.post('/api/private/farmer/requests', headers=headers,
                                         json={'assessment_id':'bad-id', 'message':'Review this'}).status_code, 404)
        json_report = self.client.get(f"/api/private/farmer/reports/{result['scenario_id']}?format=json", headers=headers)
        self.assertEqual(json_report.status_code, 200)
        self.assertEqual(json_report.json()['assessment']['cash_gap_inr'], result['stress']['cash_gap_inr'])
        csv_report = self.client.get(f"/api/private/farmer/reports/{result['scenario_id']}?format=csv", headers=headers)
        self.assertIn('field,value', csv_report.text)
        self.assertIn(result['scenario_id'], csv_report.text)
        parsed = list(csv.reader(io.StringIO(csv_report.text)))
        self.assertEqual(parsed[0], ['field', 'value'])
        self.assertIn(['cash_gap_inr', result['stress']['cash_gap_inr']], parsed)
        pdf_report = self.client.get(f"/api/private/farmer/reports/{result['scenario_id']}?format=pdf", headers=headers)
        self.assertTrue(pdf_report.content.startswith(b'%PDF-1.4'))
        self.assertIn(b'%%EOF', pdf_report.content)
        xref_at = int(pdf_report.content.rsplit(b'startxref\n', 1)[1].splitlines()[0])
        self.assertTrue(pdf_report.content[xref_at:].startswith(b'xref'))
        with _connect() as con:
            self.assertGreaterEqual(con.execute('SELECT COUNT(*) FROM access_audit WHERE action LIKE "download_%"').fetchone()[0], 3)

    def test_logout_revokes_server_session(self):
        headers = self.login_farmer('9876543210')
        self.assertEqual(self.client.get('/api/private/farmer/home', headers=headers).status_code, 200)
        self.assertEqual(self.client.post('/api/auth/logout', headers=headers).status_code, 204)
        self.assertEqual(self.client.get('/api/private/farmer/home', headers=headers).status_code, 401)

    def test_expired_access_session_is_rejected(self):
        headers = self.login_farmer('9876543210')
        token = headers['Authorization'].split(' ', 1)[1]
        from app.auth.service import decode_access_token
        jti = decode_access_token(token)['jti']
        with _connect() as con:
            con.execute("UPDATE auth_sessions SET expires_at='2000-01-01T00:00:00+00:00' WHERE jti=?", (jti,))
        self.assertEqual(self.client.get('/api/private/farmer/home', headers=headers).status_code, 401)

    def test_review_queue_uses_provisioned_branch_scope(self):
        farmer = self.login_farmer('9876543210')
        result = self.client.post('/api/scenarios/evaluate', json={'borrower_id':'B-DEMO-001'}).json()
        request = self.client.post('/api/private/farmer/requests', headers=farmer,
                                   json={'assessment_id':result['scenario_id'], 'message':'Please call me.'}).json()
        create_user(role='branch_lead', name='Pune reviewer', email='pune@example.test',
                    password='safe-password', branch_id='Pune Rural')
        create_user(role='branch_lead', name='Nashik reviewer', email='nashik@example.test',
                    password='safe-password', branch_id='Nashik Rural')
        pune = self.client.post('/api/auth/login', json={'email':'pune@example.test','password':'safe-password'}).json()
        pune_headers = {'Authorization':'Bearer '+pune['access_token']}
        self.assertEqual(self.client.get('/api/private/review/requests', headers=pune_headers).json()['requests'], [])
        self.assertEqual(self.client.patch(f"/api/private/review/requests/{request['request_id']}", headers=pune_headers,
                                           json={'status':'reviewed','note':'Not in this branch'}).status_code, 404)
        nashik = self.client.post('/api/auth/login', json={'email':'nashik@example.test','password':'safe-password'}).json()
        nashik_headers = {'Authorization':'Bearer '+nashik['access_token']}
        response = self.client.patch(f"/api/private/review/requests/{request['request_id']}", headers=nashik_headers,
                                     json={'status':'under_review','note':'Review started.'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['reviewed_by'], nashik['user']['id'])

    def test_officer_assessment_list_and_export_are_branch_scoped(self):
        create_user(role='bank_officer', name='Nashik officer', email='officer.nashik@example.test',
                    password='safe-password', branch_id='Nashik Rural')
        token = self.client.post('/api/auth/login', json={'email':'officer.nashik@example.test',
                                                          'password':'safe-password'}).json()['access_token']
        headers = {'Authorization':'Bearer '+token}
        denied = self.client.post('/api/private/officer/assessments/evaluate', headers=headers,
                                  json={'borrower_id':'B-DEMO-002'})
        self.assertEqual(denied.status_code, 404)
        saved = self.client.post('/api/private/officer/assessments/evaluate', headers=headers,
                                 json={'borrower_id':'B-DEMO-001'})
        self.assertEqual(saved.status_code, 200)
        assessment_id = saved.json()['scenario_id']
        self.assertEqual(self.client.get('/api/private/officer/assessments', headers=headers).json()['assessments'][0]['scenario_id'], assessment_id)
        report = self.client.get(f'/api/private/officer/reports/{assessment_id}?format=json', headers=headers)
        self.assertEqual(report.status_code, 200)
        self.assertEqual(report.json()['result']['result_hash'], saved.json()['result_hash'])
        self.assertEqual(self.client.get('/api/private/officer/assessments/'+assessment_id).status_code, 401)
