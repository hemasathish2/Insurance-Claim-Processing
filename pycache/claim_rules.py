"""Deterministic demonstration rules; NOT an insurance underwriting system."""
from datetime import date
RULE_VERSION = 'demo-1.0'

def evaluate(claim, existing_events=()):
    results=[]
    def add(code, name, passed, reason):
        results.append({'code':code,'name':name,'passed':passed,'reason':reason})
    incident=claim.get('incident_date')
    try: incident_date=date.fromisoformat(incident)
    except (ValueError,TypeError): incident_date=None
    active=claim.get('policy_active') is True
    add('R1','Policy active',active,'Policy active on incident date' if active else 'Policy activity must be verified by a reviewer')
    covered=claim.get('covered') is True
    add('R2','Coverage',covered,'Claim category is covered' if covered else 'Coverage is unconfirmed or not covered; manual interpretation required')
    try: amount=float(claim.get('amount')); limit=float(claim.get('policy_limit')); amount_ok=0<amount<=limit
    except (ValueError,TypeError): amount_ok=False
    add('R3','Policy limit',amount_ok,'Amount is within the demonstration policy limit' if amount_ok else 'Amount is invalid, over limit, or limit is unknown')
    docs=claim.get('document_present') is True
    add('R4','Documents',docs,'Supporting document received' if docs else 'Supporting document is missing or unreadable')
    try: window=int(claim.get('reporting_window_days',30)); within=bool(incident_date and 0<=(date.today()-incident_date).days<=window)
    except (ValueError,TypeError): within=False
    add('R5','Reporting window',within,'Incident is within the reporting window' if within else 'Incident date is invalid, future dated, or outside reporting window')
    event=(claim.get('policy_number'),incident,claim.get('category'))
    unique=bool(all(event)) and event not in existing_events
    add('R6','Duplicate event',unique,'No matching event found in stored claims' if unique else 'Possible duplicate or incomplete event identifiers; investigate')
    eligible=all(x['passed'] for x in results)
    return {'decision':'APPROVE_ELIGIBLE' if eligible else 'REFER_FOR_REVIEW','rules':results,'rule_version':RULE_VERSION,'reasons':[x['reason'] for x in results if not x['passed']]}
