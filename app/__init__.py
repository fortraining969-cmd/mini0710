import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flasgger import Swagger
from config import Config
import pandas as pd

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"))
    app.config.from_object(Config)
    db.init_app(app)
    Swagger(app)

    # ensure dataset exists and logs dir
    ensure_dataset_and_dirs(app)

    from .controllers import main_bp
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()

    # register error handlers
    from .utils import register_error_handlers
    register_error_handlers(app)

    return app

def ensure_dataset_and_dirs(app):
    path = app.config["DATASET_PATH"]
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        df = pd.DataFrame([
            {"loan_type":"Personal Loan", "min_amount":5000, "max_amount":500000, "min_tenure":6, "max_tenure":60, "interest_rate":14.5, "eligibility_score":0.6},
            {"loan_type":"Home Loan", "min_amount":200000, "max_amount":5000000, "min_tenure":60, "max_tenure":360, "interest_rate":8.5, "eligibility_score":0.8},
            {"loan_type":"Auto Loan", "min_amount":20000, "max_amount":2000000, "min_tenure":12, "max_tenure":84, "interest_rate":9.9, "eligibility_score":0.7},
            {"loan_type":"Education Loan", "min_amount":10000, "max_amount":3000000, "min_tenure":12, "max_tenure":120, "interest_rate":10.0, "eligibility_score":0.65},
            {"loan_type":"Top-up Personal", "min_amount":10000, "max_amount":250000, "min_tenure":6, "max_tenure":60, "interest_rate":16.0, "eligibility_score":0.5}
        ])
        df.to_csv(path, index=False)

    log_dir = app.config["LOG_DIR"]
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    # create activity.csv header if missing
    activity_csv = os.path.join(log_dir, "activity.csv")
    if not os.path.exists(activity_csv):
        with open(activity_csv, "w", encoding="utf-8") as f:
            f.write("timestamp,event,user_id,user_email,application_id,loan_amount,loan_status,recommended_picked,login_time,logout_time,ip,user_agent,extra\n")
