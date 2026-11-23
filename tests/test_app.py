import pytest
import app as app_module
@pytest.fixture
def client(tmp_path):
    app_module.app.config.update(TESTING=True,DATABASE=str(tmp_path/'test.db'),UPLOAD_FOLDER=str(tmp_path/'uploads'))
    app_module.init_db()
    return app_module.app.test_client()
def test_health(client):assert client.get('/api/health').json['status']=='ok'
def test_missing_fields(client):assert client.post('/claims/new',data={}).status_code==400
def test_submit_and_missing_document_routes_to_review(client):
    r=client.post('/claims/new',data={'claimant':'Synthetic Test','policy_number':'POL-01','incident_date':'2026-11-20','claim_amount':'100','category':'Vehicle'},follow_redirects=True)
    assert b'SUBMITTED' in r.data
    with app_module.db() as c:cid=c.execute('SELECT id FROM claims').fetchone()['id']
    r=client.post(f'/claims/{cid}/evaluate',data={'policy_active':'yes','covered':'yes','policy_limit':'1000','reporting_window_days':'365'},follow_redirects=True)
    assert b'HUMAN_REVIEW' in r.data
    assert b'Supporting document is missing' in r.data
    assert b'Only eligible claims' in client.post(f'/claims/{cid}/approve',follow_redirects=True).data
