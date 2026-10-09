"""Fresh-database authentication integration regressions."""
import os
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.db import _connect
from app.auth.service import seed_demo_users

class AuthVerification(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f"sqlite:///{Path(self.temp.name) / 'auth.db'}"
        self.context = TestClient(app)
        self.client = self.context.__enter__()

    def tearDown(self):
        self.context.__exit__(None, None, None)
        if self.previous is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = self.previous
        self.temp.cleanup()

    def otp(self, phone='9876543210'):
        response = self.client.post('/api/auth/otp/send', json={'phone':phone})
        self.assertEqual(response.status_code, 200)
        return response.json()['otp']

    def test_password_login_and_me(self):
        for email, role in [('officer@bank.demo','bank_officer'),('agent@insurance.demo','insurance_agent')]:
            result = self.client.post('/api/auth/login',json={'email':' '+email.upper()+' ', 'password':'password123'})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()['user']['role'], role)
            headers={'Authorization':'Bearer '+result.json()['access_token']}
            self.assertEqual(self.client.get('/api/auth/me',headers=headers).status_code,200)
        self.assertEqual(self.client.get('/api/auth/me').status_code,401)
        self.assertEqual(self.client.get('/api/auth/me',headers={'Authorization':'Bearer invalid'}).status_code,401)
        self.assertEqual(self.client.post('/api/auth/login',json={'email':email,'password':'bad'}).status_code,401)

    def test_farmer_link_and_replay_after_two_sessions(self):
        self.otp()
        code=self.otp()
        request={'phone':'9876543210','otp':code}
        result=self.client.post('/api/auth/otp/verify',json=request)
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json()['user']['linked_borrower_id'],'B-DEMO-001')
        self.assertEqual(self.client.post('/api/auth/otp/verify',json=request).status_code,400)

    def test_unrelated_phone_does_not_claim_demo_link(self):
        phone='1234563210'
        result=self.client.post('/api/auth/otp/verify',json={'phone':phone,'otp':self.otp(phone)})
        self.assertEqual(result.status_code,200)
        self.assertIsNone(result.json()['user']['linked_borrower_id'])

    def test_inactive_farmer(self):
        with _connect() as con:
            con.execute("UPDATE users SET is_active=0 WHERE phone='9876543210'")
        result=self.client.post('/api/auth/otp/verify',json={'phone':'9876543210','otp':self.otp()})
        self.assertEqual(result.status_code,403)

    def test_invalid_inputs_and_duplicate_normalization(self):
        for phone in ['abcdefghij','123','１２３４５６７８９０']:
            self.assertEqual(self.client.post('/api/auth/otp/send',json={'phone':phone}).status_code,422)
        request={'role':'bank_officer','name':'Test User','email':' OFFICER@BANK.DEMO ','password':'password123'}
        self.assertEqual(self.client.post('/api/auth/register',json=request).status_code,403)
        request['email']='other@example.com'
        request['password']='é'*40
        request={'role':'farmer','name':'Test User','phone':'1234563210','password':'é'*40}
        self.assertEqual(self.client.post('/api/auth/register',json=request).status_code,422)
        request['password']='password123'
        request['name']='   '
        self.assertEqual(self.client.post('/api/auth/register',json=request).status_code,422)

    def test_farmer_cannot_choose_a_borrower_link(self):
        response = self.client.post('/api/auth/register', json={
            'role':'farmer', 'name':'Farmer One', 'phone':'1234563210',
            'linked_borrower_id':'B-DEMO-002'
        })
        self.assertEqual(response.status_code, 403)

    def test_partial_seed_repairs_only_missing_accounts(self):
        with _connect() as con:
            con.execute("DELETE FROM users WHERE phone='9876543211'")
        seed_demo_users()
        seed_demo_users()
        with _connect() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM users').fetchone()[0],4)

    def test_expired_otp_and_inactive_password(self):
        code=self.otp()
        with _connect() as con:
            con.execute("UPDATE otp_sessions SET expires_at='2000-01-01T00:00:00+00:00'")
            con.execute("UPDATE users SET is_active=0 WHERE email='officer@bank.demo'")
        self.assertEqual(self.client.post('/api/auth/otp/verify',json={'phone':'9876543210','otp':code}).status_code,400)
        self.assertEqual(self.client.post('/api/auth/login',json={'email':'officer@bank.demo','password':'password123'}).status_code,403)
