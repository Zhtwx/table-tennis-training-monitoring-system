from functools import wraps

from flask import redirect, render_template, request, session, url_for


USERS = {
    "admin": {
        "password": "admin123",
        "name": "系统管理员",
        "role": "admin",
        "role_name": "管理员",
        "department": "训练中心",
    },
    "coach": {
        "password": "user123",
        "name": "教练用户",
        "role": "coach",
        "role_name": "普通用户",
        "department": "一队教练组",
        "coach_id": 2,
    },
}


def current_user():
    username = session.get("username")
    if not username:
        return None
    user = USERS.get(username)
    if not user:
        return None
    return {"username": username, **user}


def is_safe_redirect_url(target):
    if not target:
        return False
    target = target.strip()
    if "\r" in target or "\n" in target:
        return False
    return target.startswith("/") and not target.startswith("//")


def can_delete_training_plan(plan, user):
    if not user:
        return False
    if user["role"] == "admin":
        return True
    if user["role"] != "coach":
        return False
    try:
        return int(user.get("coach_id", 0)) == int(plan.get("coach_id", 0))
    except (TypeError, ValueError):
        return False


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return redirect(url_for("login", next=request.path))
            if user["role"] not in roles:
                return render_template("auth/forbidden.html"), 403
            return view_func(*args, **kwargs)

        return wrapper

    return decorator
