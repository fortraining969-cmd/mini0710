from . import db
from datetime import datetime
import enum
import json


class Account(db.Model):
    __tablename__ = "accounts"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    phone = db.Column(db.String(30))
    gender = db.Column(db.String(10))
    occupation = db.Column(db.String(120))
    monthly_income = db.Column(db.Float, default=0.0)
    pan = db.Column(db.String(20), nullable=True)
    aadhaar = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(200), nullable=True)  # bcrypt hash
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    applications = db.relationship("LoanApplication", back_populates="account")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "gender": self.gender,
            "occupation": self.occupation,
            "monthly_income": self.monthly_income,
            "pan": self.pan,
            "aadhaar": self.aadhaar,
            "created_at": self.created_at.isoformat()
        }


class LoanOption(db.Model):
    __tablename__ = "loan_options"
    id = db.Column(db.Integer, primary_key=True)
    loan_type = db.Column(db.String(120), nullable=False)
    min_amount = db.Column(db.Float, nullable=False)
    max_amount = db.Column(db.Float, nullable=False)
    min_tenure = db.Column(db.Integer, nullable=False)
    max_tenure = db.Column(db.Integer, nullable=False)
    interest_rate = db.Column(db.Float, nullable=False)
    eligibility_score = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "loan_type": self.loan_type,
            "min_amount": self.min_amount,
            "max_amount": self.max_amount,
            "min_tenure": self.min_tenure,
            "max_tenure": self.max_tenure,
            "interest_rate": self.interest_rate,
            "eligibility_score": self.eligibility_score
        }


class ApplicationStatus(enum.Enum):
    PENDING = "PENDING"
    SUGGESTED = "SUGGESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class LoanApplication(db.Model):
    __tablename__ = "loan_applications"
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False)
    requested_amount = db.Column(db.Float, nullable=False)
    requested_tenure = db.Column(db.Integer, nullable=False)
    selected_loan_id = db.Column(db.Integer, db.ForeignKey("loan_options.id"), nullable=True)
    custom_preferences = db.Column(db.Text, nullable=True)
    score = db.Column(db.Float, default=0.0)
    status = db.Column(db.Enum(ApplicationStatus), default=ApplicationStatus.PENDING)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    manager_comment = db.Column(db.String(512), nullable=True)
    picked_recommended = db.Column(db.Boolean, default=False)  # whether user picked recommended option

    account = db.relationship("Account", back_populates="applications")
    selected_loan = db.relationship("LoanOption")

    def to_dict(self):
        return {
            "id": self.id,
            "account": self.account.to_dict(),
            "requested_amount": self.requested_amount,
            "requested_tenure": self.requested_tenure,
            "selected_loan": self.selected_loan.to_dict() if self.selected_loan else None,
            "custom_preferences": json.loads(self.custom_preferences) if self.custom_preferences else None,
            "score": self.score,
            "status": self.status.value,
            "manager_comment": self.manager_comment,
            "picked_recommended": self.picked_recommended,
            "created_at": self.created_at.isoformat()
        }
