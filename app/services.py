from .models import LoanOption, Account, LoanApplication, ApplicationStatus
from . import db
import pandas as pd
import json
import random

from flask import current_app

def load_dataset_into_db():
    path = current_app.config["DATASET_PATH"]
    df = pd.read_csv(path)
    df = df.dropna(subset=["loan_type", "min_amount", "max_amount"])
    df["interest_rate"] = df["interest_rate"].astype(float)
    df["eligibility_score"] = df.get("eligibility_score", 0.5).astype(float)

    for _, row in df.iterrows():
        existing = LoanOption.query.filter_by(loan_type=row["loan_type"]).first()
        if existing:
            existing.min_amount = row["min_amount"]
            existing.max_amount = row["max_amount"]
            existing.min_tenure = int(row.get("min_tenure", existing.min_tenure if existing.min_tenure else 0))
            existing.max_tenure = int(row.get("max_tenure", existing.max_tenure if existing.max_tenure else 0))
            existing.interest_rate = row["interest_rate"]
            existing.eligibility_score = row["eligibility_score"]
        else:
            lo = LoanOption(
                loan_type=row["loan_type"],
                min_amount=row["min_amount"],
                max_amount=row["max_amount"],
                min_tenure=int(row.get("min_tenure", 6)),
                max_tenure=int(row.get("max_tenure", 60)),
                interest_rate=row["interest_rate"],
                eligibility_score=row["eligibility_score"]
            )
            db.session.add(lo)
    db.session.commit()

def recommend_loans(requested_amount, requested_tenure, flexible=False, flexibility_factor=0.15):
    query = LoanOption.query
    loans = query.all()
    candidates = []
    for l in loans:
        amt_penalty = 0.0
        if requested_amount < l.min_amount:
            amt_penalty = (l.min_amount - requested_amount) / l.min_amount
        elif requested_amount > l.max_amount:
            amt_penalty = (requested_amount - l.max_amount) / l.max_amount

        tenure_penalty = 0.0
        if requested_tenure < l.min_tenure:
            tenure_penalty = (l.min_tenure - requested_tenure) / l.min_tenure
        elif requested_tenure > l.max_tenure:
            tenure_penalty = (requested_tenure - l.max_tenure) / l.max_tenure

        base_score = l.eligibility_score - (amt_penalty * 0.6 + tenure_penalty * 0.4)
        if flexible:
            base_score += flexibility_factor * 0.5

        candidates.append((l, base_score))

    candidates.sort(key=lambda x: x[1], reverse=True)
    return [{"loan": c[0], "score": round(float(c[1]), 4)} for c in candidates]

def generate_custom_options(base_loan: LoanOption, requested_amount, requested_tenure, n=3):
    custom = []
    for i in range(n):
        amt = max(base_loan.min_amount, min(base_loan.max_amount, requested_amount * (1 + random.uniform(-0.25, 0.25))))
        tenure = max(base_loan.min_tenure, min(base_loan.max_tenure, int(requested_tenure * (1 + random.uniform(-0.3, 0.3)))))
        interest = max(5.0, base_loan.interest_rate * (1 + random.uniform(-0.08, 0.12)))
        custom.append({
            "loan_type": f"{base_loan.loan_type} (custom {i+1})",
            "amount": round(amt, 2),
            "tenure": tenure,
            "interest_rate": round(interest, 2),
        })
    return custom

def score_application(account: Account, loan_option: LoanOption, requested_amount, requested_tenure):
    monthly_rate = loan_option.interest_rate / 100 / 12
    n = max(1, requested_tenure)
    monthly_payment = requested_amount / n + (requested_amount * monthly_rate)
    income_factor = min(1.0, account.monthly_income / (monthly_payment * 3))
    base_score = float(loan_option.eligibility_score) * 0.6 + income_factor * 0.4
    return round(base_score, 4)

def manager_decision(application: LoanApplication):
    score = max(0.0, min(1.0, application.score))
    prob = 0.3 + 0.6 * score
    prob = max(0.05, min(0.95, prob))
    approved = random.random() < prob
    comment = "Approved by system-sim manager" if approved else "Rejected by system-sim manager (low credit match)"
    return approved, comment
