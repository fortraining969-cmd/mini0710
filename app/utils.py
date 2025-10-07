from flask import jsonify, current_app, request
from werkzeug.exceptions import HTTPException
import bcrypt
import jwt
from datetime import datetime, timedelta
from config import Config
from functools import wraps

class AppError(Exception):
    def __init__(self, message, code=400):
        super().__init__(message)
        self.message = message
        self.code = code

def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        response = jsonify({"error": err.message})
        response.status_code = err.code
        return response

    @app.errorhandler(HTTPException)
    def handle_http_exception(err):
        response = jsonify({"error": err.description})
        response.status_code = err.code or 500
        return response

    @app.errorhandler(Exception)
    def handle_generic_exception(err):
        response = jsonify({"error": "Internal Server Error", "detail": str(err)})
        response.status_code = 500
        return response

# bcrypt helpers (use bcrypt only)
def hash_password(password: str) -> str:
    if isinstance(password, str):
        password = password.encode("utf-8")
    hashed = bcrypt.hashpw(password, bcrypt.gensalt())
    return hashed.decode("utf-8")

def check_password(password: str, hashed: str) -> bool:
    if isinstance(password, str):
        password = password.encode("utf-8")
    if isinstance(hashed, str):
        hashed = hashed.encode("utf-8")
    return bcrypt.checkpw(password, hashed)

# JWT helpers
def create_token(identity: dict):

    secret = current_app.config.get("JWT_SECRET")
    algo = current_app.config.get("JWT_ALGORITHM", "HS256")
    expires = current_app.config.get("JWT_EXPIRES_DELTA", timedelta(hours=4))
    now = datetime.utcnow()
    payload = {
        "sub": str(identity["id"]),
        "iat": now,
        "exp": now + expires
    }
    token = jwt.encode(payload, secret, algorithm=algo)
    return token

def decode_token(token: str):
    secret = current_app.config.get("JWT_SECRET")
    algo = current_app.config.get("JWT_ALGORITHM", "HS256")
    try:
        payload = jwt.decode(token, secret, algorithms=[algo])
        user_id = int(payload.get("sub"))
        return user_id
    except jwt.ExpiredSignatureError:
        raise AppError("Token expired", 401)
    except Exception as e:
        raise AppError(f"Invalid token {e}", 401)

def get_token_from_request():
    # check Authorization header first, then cookie
    auth = request.headers.get("Authorization", None)
    if auth and auth.startswith("Bearer "):
        return auth.split(" ", 1)[1]
    token = request.cookies.get("access_token")
    return token

def token_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = get_token_from_request()
        if not token:
            raise AppError("Missing token", 401)
        user = decode_token(token)
        if not user:
            raise AppError("Invalid authentication", 401)
        # attach user to flask.g for route usage
        from flask import g
        user_id = decode_token(token)  # returns int
        g.current_user = user_id
        return fn(*args, **kwargs)
    return wrapper
