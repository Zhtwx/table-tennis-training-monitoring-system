# ============================================================
# 乒乓球运动员综合训练监控管理系统 · 认证与权限工具模块
# 模块职责: 提供用户会话读取、角色权限校验装饰器
# ============================================================

from functools import wraps

from flask import redirect, render_template, request, session, url_for

# ============================================================
# 用户凭据（硬编码，后续可迁移至 MySQL user_account 表）
# ============================================================

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
    },
}


def current_user():
    """获取当前登录用户信息。

    从 Flask session 中读取 username，在 USERS 字典中查找对应信息。
    返回包含 username、role、name 等字段的字典，未登录返回 None。
    """
    username = session.get("username")
    if not username:
        return None
    user = USERS.get(username)
    if not user:
        return None
    return {"username": username, **user}


def role_required(*roles):
    """角色权限校验装饰器。

    用于保护路由，确保只有指定角色的用户才能访问。
    未登录用户重定向到登录页，权限不足返回 403。

    用法:
        @role_required("admin")
        def admin_only_route():
            ...

        @role_required("admin", "coach")
        def shared_route():
            ...

    Args:
        *roles: 允许访问的角色字符串，如 "admin"、"coach"
    """
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
