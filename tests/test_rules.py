from datetime import date
from claim_rules import evaluate

def good():return {'policy_number':'POL-01','incident_date':date.today().isoformat(),'category':'Vehicle','amount':12500,'policy_limit':25000,'policy_active':True,'covered':True,'document_present':True,'reporting_window_days':30}
def test_all_pass():
    r=evaluate(good());assert r['decision']=='APPROVE_ELIGIBLE';assert len(r['rules'])==6
def test_each_rule_failure():
    for field,value in [('policy_active',False),('covered',False),('amount',25001),('document_present',False),('incident_date','invalid')]:
        c=good();c[field]=value;assert evaluate(c)['decision']=='REFER_FOR_REVIEW'
def test_duplicate():
    c=good();assert evaluate(c,{(c['policy_number'],c['incident_date'],c['category'])})['decision']=='REFER_FOR_REVIEW'
def test_boundary_amount():
    c=good();c['amount']=25000;assert evaluate(c)['decision']=='APPROVE_ELIGIBLE'
def test_missing_and_conflicting():
    c=good();c['policy_limit']=None;assert evaluate(c)['decision']=='REFER_FOR_REVIEW'
