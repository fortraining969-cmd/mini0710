import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    JWT_SECRET = "c2ccbd1fcbc19be676db3104d2bce2e9"
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRES_DELTA = timedelta(hours=4)  # token lifetime
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'loan_app.db')}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SWAGGER = {"title": "Loan Approval API", "uiversion": 3}
    DATASET_PATH = os.environ.get("DATASET_PATH", os.path.join(BASE_DIR, "dataset", "loans.csv"))
    LOG_DIR = os.environ.get("LOG_DIR", os.path.join(BASE_DIR, "logs"))
