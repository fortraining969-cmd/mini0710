import os
import csv
from collections import Counter
from config import Config

def load_activity():
    path = os.path.join(Config().LOG_DIR, "activity.csv") if hasattr(Config, "__call__") else Config.LOG_DIR
    import config as cfg
    activity_csv = os.path.join(cfg.BASE_DIR, "logs", "activity.csv")
    if not os.path.exists(activity_csv):
        print("No activity log found at", activity_csv)
        return []
    rows = []
    with open(activity_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows

def analyze_recommended_pick(rows):
    picks = [r for r in rows if r.get("event")=="PICK_OPTION"]
    total_picks = len(picks)
    recommended_true = sum(1 for r in picks if r.get("recommended_picked","").lower() in ("true","1","True","TRUE"))
    recommended_false = total_picks - recommended_true
    print("Total PICK_OPTION events:", total_picks)
    print("Picked recommended option:", recommended_true)
    print("Did not pick recommended option:", recommended_false)
    if total_picks:
        print(f"Percentage picked recommended: {recommended_true/total_picks*100:.2f}%")

def analyze_logins(rows):
    logins = [r for r in rows if r.get("event")=="LOGIN"]
    print("Total logins recorded:", len(logins))
    # unique users who logged in
    users = set(r.get("user_email") for r in logins)
    print("Unique users who logged in:", len(users))

if __name__ == "__main__":
    rows = load_activity()
    if not rows:
        exit(0)
    analyze_recommended_pick(rows)
    analyze_logins(rows)
