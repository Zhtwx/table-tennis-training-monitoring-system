import secrets
from datetime import datetime

from flask import abort, request, session


AUDIT_LOGS = []
CSRF_EXEMPT_ENDPOINTS = {"login", "static", "healthz"}


def csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def validate_csrf_token():
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return None
    if request.endpoint in CSRF_EXEMPT_ENDPOINTS:
        return None
    expected = session.get("_csrf_token")
    supplied = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not expected or not supplied or not secrets.compare_digest(expected, supplied):
        abort(400, description="CSRF token missing or invalid")
    return None


def record_audit_log(action, target_type, target_id=None, before=None, after=None, result="success", user=None):
    AUDIT_LOGS.append(
        {
            "id": len(AUDIT_LOGS) + 1,
            "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "username": user.get("username") if user else None,
            "role": user.get("role") if user else None,
            "ip": request.remote_addr,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "before": before,
            "after": after,
            "result": result,
        }
    )
