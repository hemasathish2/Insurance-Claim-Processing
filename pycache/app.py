import os
import sqlite3
import uuid
import json
from datetime import datetime
from pathlib import Path

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, jsonify
)

from claim_rules import evaluate

BASE = Path(__file__).resolve().parent

app = Flask(__name__)
app.secret_key = os.environ.get(
    "SECRET_KEY", "local-demo-only-change-before-deployment"
)

app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
app.config["DATABASE"] = os.environ.get(
    "DATABASE", str(BASE / "claims.sqlite3")
)
app.config["UPLOAD_FOLDER"] = os.environ.get(
    "UPLOAD_FOLDER", str(BASE / "uploads")
)

ALLOWED = {".pdf", ".jpg", ".jpeg", ".png", ".txt"}


def db():
    connection = sqlite3.connect(app.config["DATABASE"])
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with db() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS claims (
                id TEXT PRIMARY KEY,
                claimant TEXT NOT NULL,
                policy_number TEXT NOT NULL,
                incident_date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                filename TEXT,
                status TEXT NOT NULL,
                service_class TEXT NOT NULL,
                decision TEXT,
                rule_results TEXT,
                created_at TEXT NOT NULL,
                approved_at TEXT,
                payout_reference TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id TEXT,
                event TEXT,
                detail TEXT,
                at TEXT
            )
        """)


def log(c, claim_id, event, detail=""):
    c.execute(
        """INSERT INTO audit (claim_id, event, detail, at)
           VALUES (?, ?, ?, ?)""",
        (
            claim_id,
            event,
            detail,
            datetime.now().isoformat(timespec="seconds")
        )
    )


def all_claims():
    with db() as c:
        return c.execute(
            "SELECT * FROM claims ORDER BY created_at DESC"
        ).fetchall()


def get_claim(claim_id):
    with db() as c:
        return c.execute(
            "SELECT * FROM claims WHERE id=?",
            (claim_id,)
        ).fetchone()


def rules_passed(claim):
    if claim["decision"] != "APPROVE_ELIGIBLE":
        return False

    try:
        rules = json.loads(claim["rule_results"] or "[]")
    except (ValueError, TypeError):
        return False

    return (
        isinstance(rules, list)
        and len(rules) == 6
        and all(
            isinstance(rule, dict)
            and rule.get("passed") is True
            for rule in rules
        )
    )


def review_completed(c, claim_id):
    row = c.execute(
        """SELECT id FROM audit
           WHERE claim_id=? AND event='REVIEW_COMPLETED'
           ORDER BY id DESC LIMIT 1""",
        (claim_id,)
    ).fetchone()

    return row is not None


@app.route("/")
def home():
    claims = all_claims()

    return render_template(
        "index.html",
        claims=claims,
        total=len(claims),
        review=sum(
            x["status"] == "HUMAN_REVIEW" for x in claims
        ),
        eligible=sum(
            x["status"] == "ELIGIBLE_REVIEW" for x in claims
        ),
        payout=sum(
            x["status"] == "PAYOUT_QUEUED" for x in claims
        )
    )


@app.route("/claims/new", methods=["GET", "POST"])
def new_claim():
    if request.method == "GET":
        return render_template("new.html")

    claimant = request.form.get("claimant", "").strip()
    policy = request.form.get("policy_number", "").strip()
    incident = request.form.get("incident_date", "").strip()
    category = request.form.get("category", "").strip()

    try:
        amount = float(request.form.get("claim_amount", ""))
    except (ValueError, TypeError):
        amount = 0

    if (
        not all((claimant, policy, incident, category))
        or not (0 < amount < float("inf"))
    ):
        flash(
            "Enter all required fields and a positive amount.",
            "error"
        )
        return render_template("new.html"), 400

    try:
        datetime.strptime(incident, "%Y-%m-%d")
    except ValueError:
        flash("Enter a valid incident date.", "error")
        return render_template("new.html"), 400

    file = request.files.get("document")
    filename = None

    if file and file.filename:
        ext = Path(file.filename).suffix.lower()

        if ext not in ALLOWED:
            flash(
                "Only PDF, JPG, PNG and TXT files are supported.",
                "error"
            )
            return render_template("new.html"), 400

        filename = uuid.uuid4().hex + ext

        Path(app.config["UPLOAD_FOLDER"]).mkdir(
            parents=True,
            exist_ok=True
        )

        file.save(
            Path(app.config["UPLOAD_FOLDER"]) / filename
        )

    claim_id = (
        "CLM-"
        + datetime.now().strftime("%Y%m%d")
        + "-"
        + uuid.uuid4().hex[:6].upper()
    )

    with db() as c:
        c.execute("""
            INSERT INTO claims (
                id, claimant, policy_number,
                incident_date, amount, category,
                filename, status, service_class,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            claim_id,
            claimant,
            policy,
            incident,
            amount,
            category,
            filename,
            "SUBMITTED",
            "Normal",
            datetime.now().isoformat(timespec="seconds")
        ))

        log(
            c,
            claim_id,
            "SUBMITTED",
            "Claim intake received; document: "
            + str(bool(filename))
        )

    flash(
        "Claim submitted successfully. Reference: " + claim_id,
        "success"
    )

    return redirect(
        url_for("claim_detail", claim_id=claim_id)
    )


@app.route("/claims/<claim_id>")
def claim_detail(claim_id):
    claim = get_claim(claim_id)

    if not claim:
        return "Claim not found", 404

    with db() as c:
        audit = c.execute(
            """SELECT * FROM audit
               WHERE claim_id=?
               ORDER BY id DESC""",
            (claim_id,)
        ).fetchall()

    try:
        rules = json.loads(claim["rule_results"] or "[]")
    except (ValueError, TypeError):
        rules = []

    return render_template(
        "detail.html",
        claim=claim,
        audit=audit,
        rules=rules,
        all_rules_passed=rules_passed(claim)
    )


@app.route("/claims/<claim_id>/evaluate", methods=["POST"])
def run_rules(claim_id):
    claim = get_claim(claim_id)

    if not claim:
        return "Claim not found", 404

    if claim["status"] == "PAYOUT_QUEUED":
        flash(
            "This demo payout has already been queued.",
            "error"
        )
        return redirect(
            url_for("claim_detail", claim_id=claim_id)
        )

    policy_active = request.form.get("policy_active") == "yes"
    covered = request.form.get("covered") == "yes"

    try:
        limit = float(
            request.form.get("policy_limit", "0")
        )
        window = int(
            request.form.get("reporting_window_days", "30")
        )
    except (ValueError, TypeError):
        flash("Invalid policy settings.", "error")
        return redirect(
            url_for("claim_detail", claim_id=claim_id)
        )

    if not (0 <= limit < float("inf")) or window < 0:
        flash("Invalid policy settings.", "error")
        return redirect(
            url_for("claim_detail", claim_id=claim_id)
        )

    with db() as c:
        events = {
            (
                x["policy_number"],
                x["incident_date"],
                x["category"]
            )
            for x in c.execute(
                """SELECT policy_number, incident_date, category
                   FROM claims WHERE id != ?""",
                (claim_id,)
            ).fetchall()
        }

        data = {
            "policy_number": claim["policy_number"],
            "incident_date": claim["incident_date"],
            "category": claim["category"],
            "amount": claim["amount"],
            "policy_limit": limit,
            "reporting_window_days": window,
            "policy_active": policy_active,
            "covered": covered,
            "document_present": bool(claim["filename"])
        }

        result = evaluate(data, events)

        # All claims must complete human review before payout.
        status = "HUMAN_REVIEW"
        service = "Normal"

        c.execute("""
            UPDATE claims
            SET status=?,
                decision=?,
                service_class=?,
                rule_results=?
            WHERE id=?
        """, (
            status,
            result["decision"],
            service,
            json.dumps(result["rules"]),
            claim_id
        ))

        # A fresh rule check invalidates any earlier review completion.
        c.execute(
            """DELETE FROM audit
               WHERE claim_id=? AND event='REVIEW_COMPLETED'""",
            (claim_id,)
        )

        log(
            c,
            claim_id,
            "RULE_CHECK",
            json.dumps({
                "decision": result["decision"],
                "version": result["rule_version"],
                "reasons": result["reasons"]
            })
        )

    flash(
        "Rules evaluated. Human review is required before "
        "demo payout authorisation.",
        "success"
    )

    return redirect(
        url_for("claim_detail", claim_id=claim_id)
    )


@app.route(
    "/claims/<claim_id>/complete-review",
    methods=["POST"]
)
def complete_review(claim_id):
    claim = get_claim(claim_id)

    if not claim:
        return "Claim not found", 404

    if claim["status"] != "HUMAN_REVIEW":
        flash(
            "Claim is not awaiting human review.",
            "error"
        )
        return redirect(
            url_for("claim_detail", claim_id=claim_id)
        )

    if not rules_passed(claim):
        flash(
            "All six eligibility rules must pass before "
            "review completion.",
            "error"
        )
        return redirect(
            url_for("claim_detail", claim_id=claim_id)
        )

    with db() as c:
        c.execute("""
            UPDATE claims
            SET status=?, service_class=?
            WHERE id=? AND status='HUMAN_REVIEW'
        """, (
            "ELIGIBLE_REVIEW",
            "Normal",
            claim_id
        ))

        log(
            c,
            claim_id,
            "REVIEW_COMPLETED",
            "Human review completed by local demo operator"
        )

    flash(
        "Human review completed. Demo payout "
        "authorisation is now available.",
        "success"
    )

    return redirect(
        url_for("claim_detail", claim_id=claim_id)
    )


@app.route("/claims/<claim_id>/approve", methods=["POST"])
def approve(claim_id):
    claim = get_claim(claim_id)

    if not claim:
        return "Claim not found", 404

    if (
        claim["status"] != "ELIGIBLE_REVIEW"
        or not rules_passed(claim)
    ):
        flash(
            "Claim is not eligible for demo payout.",
            "error"
        )
        return redirect(
            url_for("claim_detail", claim_id=claim_id)
        )

    reference = "PAY-" + uuid.uuid4().hex[:10].upper()

    with db() as c:
        if not review_completed(c, claim_id):
            flash(
                "Human review must be completed first.",
                "error"
            )
            return redirect(
                url_for("claim_detail", claim_id=claim_id)
            )

        updated = c.execute("""
            UPDATE claims
            SET status=?,
                approved_at=?,
                payout_reference=?
            WHERE id=? AND status='ELIGIBLE_REVIEW'
        """, (
            "PAYOUT_QUEUED",
            datetime.now().isoformat(timespec="seconds"),
            reference,
            claim_id
        ))

        if updated.rowcount != 1:
            flash(
                "Claim status changed. Please refresh.",
                "error"
            )
            return redirect(
                url_for("claim_detail", claim_id=claim_id)
            )

        log(
            c,
            claim_id,
            "PAYOUT_QUEUED",
            "Demo payout authorised by local operator; "
            "no actual payment. " + reference
        )

    flash(
        "Demo payout queued successfully. "
        "No real money transferred.",
        "success"
    )

    return redirect(
        url_for("claim_detail", claim_id=claim_id)
    )


@app.route("/claims/<claim_id>/review", methods=["POST"])
def request_review(claim_id):
    claim = get_claim(claim_id)

    if not claim:
        return "Claim not found", 404

    if claim["status"] == "PAYOUT_QUEUED":
        flash(
            "Queued payouts cannot be returned to review "
            "through this demo action.",
            "error"
        )
        return redirect(
            url_for("claim_detail", claim_id=claim_id)
        )

    with db() as c:
        c.execute("""
            UPDATE claims
            SET status=?, service_class=?
            WHERE id=?
        """, (
            "HUMAN_REVIEW",
            "Normal",
            claim_id
        ))

        c.execute(
            """DELETE FROM audit
               WHERE claim_id=? AND event='REVIEW_COMPLETED'""",
            (claim_id,)
        )

        log(
            c,
            claim_id,
            "HUMAN_REVIEW",
            "Manual review or appeal requested"
        )

    flash("Human review requested.", "success")

    return redirect(
        url_for("claim_detail", claim_id=claim_id)
    )


@app.route("/board")
def board():
    return render_template(
        "board.html",
        claims=all_claims()
    )


@app.route("/reports")
def reports():
    return render_template(
        "reports.html",
        claims=all_claims()
    )


@app.route("/extraction")
def extraction():
    return render_template("extraction.html")


@app.route("/api/health")
def health():
    return jsonify(
        status="ok",
        service="Case17 academic prototype"
    )


@app.errorhandler(413)
def too_large(e):
    return "File exceeds 2 MB upload limit", 413


init_db()

if __name__ == "__main__":
    app.run(
        debug=os.environ.get("FLASK_DEBUG") == "1",
        port=5001
    )