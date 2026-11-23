# Case 17 — Insurance Claim Processing

A runnable **Flask + SQLite academic demonstration** based on the uploaded 17-page Case 17 report. Uses synthetic data only. No external AI API, insurer policy system, payment gateway, user authentication, or actual SonarQube instance is connected.

## Run on MacBook (VS Code or Terminal)

1. Unzip the downloaded project.
2. Open the project folder in VS Code, then open Terminal → New Terminal.
3. Run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

4. Open **http://127.0.0.1:5001** in Chrome or Safari.
5. Click **New claim**, enter synthetic data, and attach `samples/sample_document.txt`.
6. Open the new claim, enter demonstration policy settings, click **Run R1–R6 checks**, then view the rule-by-rule explanation.
7. If all six rules pass, an authorised demo operator can click **Authorise demo payout queue**. This never transfers money.
8. Use **Kanban**, **Extraction review**, and **Reports** to explore the remaining screens.

**Tip:** For a successful demo eligibility result, use a recent incident date, an uploaded document, policy active = Yes, category covered = Yes, and a policy limit greater than the claim amount. The duplicate check refers repeated policy/date/category combinations for review.

## Tests

```bash
python -m pytest -q tests
```

### Optional Selenium browser automation
Start the Flask app in one terminal. In a second terminal activate `.venv` and run:

```bash
python selenium_claim_upload.py
```

Chrome and a compatible Selenium-managed ChromeDriver are required. The script saves `selenium_submission.png` and asserts that the claim was submitted. Date input behavior can vary by Chrome locale; if necessary adjust the script's date entry.

## Reference screenshots from the report

1. Intake → `/claims/new`
2. ChatGPT-assisted field extraction → `/extraction` (static comparison only, **not live AI**)
3. Six rules → open a claim and run checks
4. Kanban → `/board`
5. Approval and payout → open an eligible claim and queue a **demo** payout
6. Document integration tests → `tests/test_app.py` and pytest terminal output
7. Selenium → run `selenium_claim_upload.py` and capture its output
8. Defect-risk heuristic → `/reports` (illustrative data)
9. SonarQube → requires a **separate real SonarQube scan**; no scan results are fabricated
10. Explainable decision → open a claim that needs review and read its rule reasons

## Design notes / limitations

- Three increments: intake, rule check, payout queue. Rule version: `demo-1.0`.
- Six explicit checks: policy active, coverage, amount limit, supporting documents, reporting window, duplicates.
- A claim never enters the demo payout queue until it passes rules and an operator explicitly authorises it.
- The local prototype does not verify the entered policy settings with an insurer. Those settings are manually entered by the user and are **not trusted proof**.
- No production authentication, access control, malware scanning, encryption at rest, data retention policy, role management, or secure storage. **Do not deploy publicly or enter personal information.**
- Uploaded files are stored locally and not exposed by a download route; size limited to 2 MB, extension allowlist enforced. This is not a complete production upload security control.
- Extraction comparison, defect-risk figures, and the 2,000/week and 60% scenario are educational reference material, not live operational metrics.
- Docker and Jenkins files are starter examples. Harden and validate before any real deployment.
- To reset demo data, stop the app and delete `claims.sqlite3`; remove test files from `uploads/` if desired.
