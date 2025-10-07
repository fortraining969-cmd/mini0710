import os
import csv
from datetime import datetime
from flask import current_app
import logging
from logging.handlers import RotatingFileHandler
import json

# Setup application logger
def setup_app_logger(app):
    log_dir = app.config.get("LOG_DIR")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "app.log")
    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

def log_activity(event, user_id=None, user_email=None, application_id=None, loan_amount=None, loan_status=None, recommended_picked=None, login_time=None, logout_time=None, ip=None, user_agent=None, extra=None):
    """
    Append a record to logs/activity.csv with fields:
    timestamp,event,user_id,user_email,application_id,loan_amount,loan_status,recommended_picked,login_time,logout_time,ip,user_agent,extra
    event: LOGIN, LOGOUT, APPLICATION_CREATED, MANAGER_DECISION, PICK_OPTION
    """
    log_dir = current_app.config.get("LOG_DIR")
    activity_csv = os.path.join(log_dir, "activity.csv")
    ts = datetime.utcnow().isoformat()
    extra_str = json.dumps(extra) if extra else ""
    # ensure file exists and headers present handled by create_app
    row = [ts, event, user_id or "", user_email or "", application_id or "", loan_amount or "", loan_status or "", bool(recommended_picked) if recommended_picked is not None else "", login_time or "", logout_time or "", ip or "", user_agent or "", extra_str]
    with open(activity_csv, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)
    # also log to app logger
    current_app.logger.info(f"event={event} user={user_email or user_id} app={application_id} amount={loan_amount} status={loan_status} recommended_picked={recommended_picked}")
