from flask import Blueprint, render_template, request, redirect, url_for, current_app, jsonify, make_response, g
from . import db
from .models import Account, LoanOption, LoanApplication, ApplicationStatus
from .services import load_dataset_into_db, recommend_loans, generate_custom_options, score_application, manager_decision
from .utils import AppError, hash_password, check_password, create_token, token_required, decode_token, get_token_from_request
from .logger import log_activity, setup_app_logger
import json
from datetime import datetime

main_bp = Blueprint("main", __name__)

@main_bp.before_app_request
def init_app():
    load_dataset_into_db()
    setup_app_logger(current_app)

@main_bp.route("/")
def index():
    return render_template("index.html")

@main_bp.route("/account/check", methods=["GET", "POST"])
def account_check():
    if request.method == "GET":
        return render_template("account_check.html")
    email = request.form.get("email")
    if not email:
        raise AppError("Email required", 400)
    account = Account.query.filter_by(email=email).first()
    if account:
        # redirect to login page (existing)
        return redirect(url_for("main.login", email=email))
    else:
        return redirect(url_for("main.create_account", email=email))

@main_bp.route("/account/create", methods=["GET", "POST"])
def create_account():
    if request.method == "GET":
        email = request.args.get("email", "")
        return render_template("account_create.html", email=email)
    data = request.form
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    if not name or not email or not password:
        raise AppError("Name, email and password are required", 400)
    existing = Account.query.filter_by(email=email).first()
    if existing:
        raise AppError("Account with this email already exists", 400)
    account = Account(
        name=name,
        email=email,
        phone=data.get("phone"),
        gender=data.get("gender"),
        occupation=data.get("occupation"),
        monthly_income=float(data.get("monthly_income") or 0.0),
        pan=data.get("pan") or None,
        aadhaar=data.get("aadhaar") or None,
        password_hash=hash_password(password)
    )
    db.session.add(account)
    db.session.commit()
    # After creation, redirect to login page as requested
    return redirect(url_for("main.login", email=account.email))

@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        email = request.args.get("email", "")
        return render_template("login.html", email=email)
    data = request.form
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        raise AppError("Email and password required", 400)
    account = Account.query.filter_by(email=email).first()
    if not account:
        raise AppError("Account not found", 404)
    if not account.password_hash or not check_password(password, account.password_hash):
        raise AppError("Invalid credentials", 401)
    # create JWT
    token = create_token({"id": account.id, "email": account.email})
    resp = make_response(redirect(url_for("main.loan_request")))
    # set cookie
    resp.set_cookie("access_token", token, httponly=True, samesite="Lax")
    # log login event
    ip = request.remote_addr
    ua = request.headers.get("User-Agent")
    login_time = datetime.utcnow().isoformat()
    log_activity(event="LOGIN", user_id=account.id, user_email=account.email, login_time=login_time, ip=ip, user_agent=ua)
    return resp

@main_bp.route("/logout", methods=["POST"])
def logout():
    token = get_token_from_request()
    user = None
    try:
        user = decode_token(token) if token else None
    except Exception:
        user = None
    resp = make_response(redirect(url_for("main.index")))
    resp.delete_cookie("access_token")
    ip = request.remote_addr
    ua = request.headers.get("User-Agent")
    logout_time = datetime.utcnow().isoformat()
    if user:
        log_activity(event="LOGOUT", user_id=user.get("id"), user_email=user.get("email"), logout_time=logout_time, ip=ip, user_agent=ua)
    return resp

@main_bp.route("/loan/request", methods=["GET", "POST"])
@token_required
def loan_request():
    user_id = g.current_user
    account = Account.query.get_or_404(user_id)
    if request.method == "GET":
        options = LoanOption.query.all()
        return render_template("loan_request.html", account=account, options=options)
    requested_amount = float(request.form.get("amount"))
    requested_tenure = int(request.form.get("tenure"))
    flexible = request.form.get("flexible") == "on"
    recs = recommend_loans(requested_amount, requested_tenure, flexible=flexible)
    top = recs[0]["loan"] if recs else None
    application = LoanApplication(
        account_id=account.id,
        requested_amount=requested_amount,
        requested_tenure=requested_tenure,
        selected_loan_id=top.id if top else None,
        custom_preferences=json.dumps({}),
        status=ApplicationStatus.SUGGESTED
    )
    application.score = score_application(account, top, requested_amount, requested_tenure) if top else 0.0
    db.session.add(application)
    db.session.commit()
    # log application creation
    ip = request.remote_addr
    ua = request.headers.get("User-Agent")
    log_activity(event="APPLICATION_CREATED", user_id=account.id, user_email=account.email, application_id=application.id, loan_amount=requested_amount, loan_status=application.status.value, ip=ip, user_agent=ua)
    return render_template("loan_options.html", account=account, application=application, recs=recs)

@main_bp.route("/loan/options/<int:app_id>/select", methods=["POST"])
@token_required
def loan_select(app_id):
    app_obj = LoanApplication.query.get_or_404(app_id)
    account = Account.query.get_or_404(app_obj.account_id)
    choice = request.form.get("choice")
    ip = request.remote_addr
    ua = request.headers.get("User-Agent")
    if choice == "custom":
        base_loan_id = int(request.form.get("base_loan_id"))
        base = LoanOption.query.get_or_404(base_loan_id)
        custom_options = generate_custom_options(base, app_obj.requested_amount, app_obj.requested_tenure, n=3)
        return render_template("loan_options.html", account=account, application=app_obj, recs=None, custom_options=custom_options, base=base)
    else:
        selected_id = int(choice)
        # detect if selected loan equals the top recommended (we stored earlier in selected_loan_id but recalc)
        recs = recommend_loans(app_obj.requested_amount, app_obj.requested_tenure, flexible=False)
        top_id = recs[0]["loan"].id if recs else None
        app_obj.selected_loan_id = selected_id
        app_obj.status = ApplicationStatus.PENDING
        app_obj.picked_recommended = (selected_id == top_id)
        db.session.commit()
        # log pick option
        log_activity(event="PICK_OPTION", user_id=account.id, user_email=account.email, application_id=app_obj.id, loan_amount=app_obj.requested_amount, loan_status=app_obj.status.value, recommended_picked=app_obj.picked_recommended, ip=ip, user_agent=ua)
        return redirect(url_for("main.manager_review", app_id=app_obj.id))

@main_bp.route("/manager/review/<int:app_id>", methods=["GET", "POST"])
@token_required
def manager_review(app_id):
    app_obj = LoanApplication.query.get_or_404(app_id)
    account = Account.query.get_or_404(app_obj.account_id)
    if request.method == "GET":
        return render_template("manager_review.html", application=app_obj)
    approved, comment = manager_decision(app_obj)
    app_obj.manager_comment = comment
    app_obj.status = ApplicationStatus.APPROVED if approved else ApplicationStatus.REJECTED
    db.session.commit()
    # log manager decision
    ip = request.remote_addr
    ua = request.headers.get("User-Agent")
    log_activity(event="MANAGER_DECISION", user_id=account.id, user_email=account.email, application_id=app_obj.id, loan_amount=app_obj.requested_amount, loan_status=app_obj.status.value, recommended_picked=app_obj.picked_recommended, ip=ip, user_agent=ua, extra={"comment": comment})
    recs = recommend_loans(app_obj.requested_amount, app_obj.requested_tenure, flexible=True)
    second_best = recs[1] if len(recs) > 1 else None
    return render_template("result.html", application=app_obj, second_best=second_best)

# API endpoint (swagger) to create account via JSON
@main_bp.route("/api/accounts", methods=["POST"])
def api_create_account():
    data = request.get_json() or {}
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    if not name or not email or not password:
        raise AppError("name, email and password required", 400)
    existing = Account.query.filter_by(email=email).first()
    if existing:
        raise AppError("Account already exists", 400)
    account = Account(name=name, email=email, monthly_income=float(data.get("monthly_income") or 0.0), password_hash=hash_password(password))
    db.session.add(account)
    db.session.commit()
    return jsonify({"account": account.to_dict()})
