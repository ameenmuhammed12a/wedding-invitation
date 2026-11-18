import csv
import io
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path
from werkzeug.security import generate_password_hash
from app import create_app

class RSVPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password='a-long-test-password'
        cls.password_hash=generate_password_hash(cls.password,method='pbkdf2:sha256:1000000')
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.database=str(Path(self.tmp.name)/'rsvp.sqlite3')
        self.app=create_app({'TESTING':True,'SECRET_KEY':'test-only-secret','ADMIN_HASH':self.password_hash,'DATABASE':self.database,'SESSION_COOKIE_SECURE':False})
        self.client=self.app.test_client()
        self.client.get('/')
        with self.client.session_transaction() as s: self.token=s['csrf']
    def tearDown(self): self.tmp.cleanup()
    def send(self,**changes):
        data=dict(name='Test Guest',guestSide='both',attending=True,guests=3,message='See you!',requestId='test-submission-id-123456')
        data.update(changes)
        return self.client.post('/api/rsvp',json=data,headers={'X-CSRF-Token':self.token})
    def login(self):
        return self.client.post('/admin/login',data={'password':self.password,'csrf_token':self.token})
    def test_saved_and_persistent(self):
        self.assertEqual(self.send().status_code,201)
        with sqlite3.connect(self.database) as db:
            self.assertEqual(db.execute('SELECT name,guests,side FROM rsvps').fetchone(),('Test Guest',3,'both'))
        self.assertEqual(self.login().status_code,302)
        self.assertIn(b'Test Guest',self.client.get('/admin').data)
    def test_retry_no_duplicate(self):
        self.send(); self.assertEqual(self.send().status_code,200)
        self.assertEqual(self.send(guests=2).status_code,409)
        with sqlite3.connect(self.database) as db: self.assertEqual(db.execute('SELECT count(*) FROM rsvps').fetchone()[0],1)
    def test_decline(self): self.assertEqual(self.send(attending=False,guests=0,guestSide=None).status_code,201)
    def test_validation(self):
        for change in [{'name':''},{'name':'x'*121},{'attending':'yes'},{'guests':True},{'guests':5},{'attending':False,'guests':1},{'message':'x'*2001},{'guestSide':'invalid'},{'requestId':'short'}]:
            with self.subTest(change=change): self.assertEqual(self.send(**change).status_code,400)
    def test_csrf_and_private_pages(self):
        self.assertEqual(self.client.post('/api/rsvp',json={}).status_code,403)
        self.assertEqual(self.client.get('/admin').status_code,302)
        self.assertEqual(self.client.get('/admin/export.csv').status_code,302)
        self.assertEqual(self.client.get('/static/../instance/config.json').status_code,404)
    def test_escape_export_logout(self):
        self.send(name='<script>alert(1)</script>',message='=HYPERLINK("bad")')
        self.login()
        page=self.client.get('/admin').data
        self.assertIn(b'&lt;script&gt;',page)
        rows=list(csv.reader(io.StringIO(self.client.get('/admin/export.csv').data.decode('utf-8-sig'))))
        self.assertTrue(rows[1][4].startswith("'="))
        with self.client.session_transaction() as s: token=s['csrf']
        self.assertEqual(self.client.post('/admin/logout',data={'csrf_token':token}).status_code,302)
        self.assertEqual(self.client.get('/admin').status_code,302)
    def test_filter(self):
        self.send();self.login()
        self.assertNotIn(b'Test Guest',self.client.get('/admin?status=no').data)
        self.assertEqual(len(list(csv.reader(io.StringIO(self.client.get('/admin/export.csv?side=bride').data.decode('utf-8-sig'))))),1)
    def test_login_throttle(self):
        for _ in range(10): self.client.post('/admin/login',data={'password':'wrong','csrf_token':self.token})
        self.assertEqual(self.client.post('/admin/login',data={'password':'wrong','csrf_token':self.token}).status_code,429)
    def test_rsvp_throttle(self):
        for i in range(30): self.assertEqual(self.send(requestId=f'test-request-number-{i:06}').status_code,201)
        self.assertEqual(self.send(requestId='test-request-number-999999').status_code,429)

if __name__=='__main__': unittest.main()
