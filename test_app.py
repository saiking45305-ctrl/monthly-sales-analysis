import os
from pathlib import Path
import pytest
@pytest.fixture
def client(tmp_path, monkeypatch):
    db=tmp_path/'test.sqlite3'; monkeypatch.setenv('DATABASE_PATH',str(db)); monkeypatch.setenv('SECRET_KEY','test-secret')
    import app as module; module.DB_PATH=str(db); module.app.config.update(TESTING=True, SECRET_KEY='test-secret')
    with module.app.test_client() as client:
        yield client

def token(client):
    with client.session_transaction() as s: return s['csrf']
def test_register_login_and_dashboard(client):
    r=client.get('/register'); assert r.status_code==200
    r=client.post('/register',data={'csrf_token':token(client),'company':'Acme','username':'owner','password':'secret1','confirm':'secret1'},follow_redirects=True); assert b'Your dashboard is ready' in r.data
    r=client.post('/sales',data={'csrf_token':token(client),'sale_date':'2026-01-01','product':'Widget','quantity':'2','unit_price':'50'},follow_redirects=True); assert b'Sale added' in r.data
    r=client.get('/api/analytics'); assert r.json['total_revenue']==100.0

def test_csrf_required(client):
    r=client.post('/register',data={'company':'Acme','username':'owner','password':'secret1','confirm':'secret1'}); assert r.status_code==400
