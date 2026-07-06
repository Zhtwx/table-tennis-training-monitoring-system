from functools import wraps

from flask import (
    Blueprint,
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)


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

NAV_ITEMS = [
    {"label": "综合看板", "endpoint": "index", "roles": {"admin", "coach"}},
    {"label": "运动员档案", "endpoint": "players.list", "roles": {"admin", "coach"}},
    {"label": "训练计划", "endpoint": "training.plans", "roles": {"admin", "coach"}},
    {"label": "专项技术录入", "endpoint": "training.batch_import", "roles": {"admin", "coach"}},
    {"label": "体能测试", "endpoint": "fitness.tests", "roles": {"admin", "coach"}},
    {"label": "伤病记录", "endpoint": "injuries.list", "roles": {"admin", "coach"}},
    {"label": "康复跟踪", "endpoint": "rehab.list", "roles": {"admin", "coach"}},
    {"label": "比赛成绩", "endpoint": "matches.list", "roles": {"admin", "coach"}},
    {"label": "用户权限", "endpoint": "auth.users", "roles": {"admin"}},
    {"label": "系统配置", "endpoint": "settings.dictionary", "roles": {"admin"}},
]

PLAYERS = [
    {
        "id": 1,
        "student_no": "2026001",
        "name": "王一鸣",
        "gender": "男",
        "age": 19,
        "level": "一级运动员",
        "level_code": "first",
        "play_style": "右手横板快攻结合弧圈",
        "injury_status": "健康",
        "injury_status_code": "healthy",
    },
    {
        "id": 2,
        "student_no": "2026002",
        "name": "李清扬",
        "gender": "女",
        "age": 18,
        "level": "二级运动员",
        "level_code": "second",
        "play_style": "左手横板两面弧圈",
        "injury_status": "观察中",
        "injury_status_code": "observe",
    },
    {
        "id": 3,
        "student_no": "2026003",
        "name": "陈昊然",
        "gender": "男",
        "age": 21,
        "level": "国家级",
        "level_code": "national",
        "play_style": "右手直板近台快攻",
        "injury_status": "康复中",
        "injury_status_code": "rehab",
    },
    {
        "id": 4,
        "student_no": "2026004",
        "name": "赵若溪",
        "gender": "女",
        "age": 20,
        "level": "一级运动员",
        "level_code": "first",
        "play_style": "右手横板反手快拨",
        "injury_status": "伤病中",
        "injury_status_code": "injured",
    },
]

MODULE_FEATURES = {
    "训练计划管理": [
        {"title": "训练周期", "desc": "按周、月、赛前周期安排训练目标与重点。"},
        {"title": "计划执行", "desc": "跟踪训练完成情况、负荷变化和教练反馈。"},
        {"title": "计划调整", "desc": "根据运动员状态及时调整训练内容和强度。"},
        {"title": "计划归档", "desc": "沉淀历史训练计划，便于复盘与对比。"},
    ],
    "体能测试评估": [
        {"title": "测试记录", "desc": "录入速度、力量、耐力、灵敏等体能指标。"},
        {"title": "等级评估", "desc": "结合队内标准形成体能等级和风险提示。"},
        {"title": "趋势分析", "desc": "跟踪单项体能指标的长期变化。"},
        {"title": "训练建议", "desc": "辅助教练制定针对性体能提升方案。"},
    ],
    "伤病记录管理": [
        {"title": "伤病档案", "desc": "记录伤病部位、时间、程度和处理方案。"},
        {"title": "风险标记", "desc": "对重点关注运动员进行健康风险提示。"},
        {"title": "复诊跟踪", "desc": "维护复查、治疗和恢复过程记录。"},
        {"title": "历史查询", "desc": "快速查看运动员过往伤病情况。"},
    ],
    "康复跟踪预警": [
        {"title": "康复计划", "desc": "安排阶段性康复目标和训练限制。"},
        {"title": "恢复进度", "desc": "记录疼痛、活动度、训练适应等恢复指标。"},
        {"title": "预警提醒", "desc": "对异常恢复进度和复发风险进行提示。"},
        {"title": "复训评估", "desc": "辅助判断运动员是否适合恢复正常训练。"},
    ],
    "比赛成绩报告": [
        {"title": "成绩记录", "desc": "维护比赛时间、对手、比分和名次。"},
        {"title": "技战术复盘", "desc": "总结发接发、相持、关键分等表现。"},
        {"title": "对手分析", "desc": "沉淀重点对手特征和历史交手记录。"},
        {"title": "报告输出", "desc": "形成面向教练组的阶段性比赛报告。"},
    ],
    "系统配置": [
        {"title": "数据字典", "desc": "统一维护运动等级、训练强度、伤病状态等选项。"},
        {"title": "基础参数", "desc": "配置系统名称、训练周期、导入字段等基础信息。"},
        {"title": "导入模板", "desc": "维护 Excel 批量导入模板和字段规则。"},
        {"title": "系统维护", "desc": "支持基础配置检查和运行状态维护。"},
    ],
    "新增运动员": [
        {"title": "基础信息", "desc": "录入姓名、性别、年龄、联系方式等基础档案。"},
        {"title": "竞技信息", "desc": "维护运动等级、打法、持拍手和专项特点。"},
        {"title": "健康状态", "desc": "同步初始健康状态与重点关注标签。"},
        {"title": "档案提交", "desc": "提交后进入运动员档案统一管理。"},
    ],
    "编辑运动员": [
        {"title": "档案更新", "desc": "更新运动员基础资料和竞技信息。"},
        {"title": "状态维护", "desc": "调整当前训练、健康和参赛状态。"},
        {"title": "记录关联", "desc": "关联训练、伤病、体能和比赛数据。"},
        {"title": "变更确认", "desc": "保存后同步更新档案列表。"},
    ],
    "历史伤病": [
        {"title": "伤病时间线", "desc": "查看运动员历次伤病发生和恢复情况。"},
        {"title": "治疗记录", "desc": "追踪处理方案、复诊结论和训练限制。"},
        {"title": "复发风险", "desc": "辅助识别长期高风险部位。"},
        {"title": "归档查询", "desc": "为训练计划调整提供依据。"},
    ],
}


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-secret-key-change-before-production"

    @app.context_processor
    def inject_layout_data():
        user = current_user()
        role = user["role"] if user else None
        visible_nav_items = [
            item for item in NAV_ITEMS if role and role in item["roles"]
        ]
        return {
            "current_user": user,
            "nav_items": visible_nav_items,
        }

    @app.before_request
    def require_login():
        public_endpoints = {"login", "static"}
        if request.endpoint in public_endpoints:
            return None
        if not session.get("username"):
            return redirect(url_for("login", next=request.path))
        return None

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if session.get("username"):
            return redirect(url_for("index"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            user = USERS.get(username)

            if user and user["password"] == password:
                session["username"] = username
                flash(f"欢迎回来，{user['name']}。", "success")
                next_url = request.args.get("next") or url_for("index")
                return redirect(next_url)

            flash("用户名或密码错误，请重新输入。", "danger")

        return render_template("auth/login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("您已安全退出系统。", "success")
        return redirect(url_for("login"))

    @app.route("/")
    @role_required("admin", "coach")
    def index():
        return render_template("index.html")

    players_bp = Blueprint("players", __name__, url_prefix="/players")

    @players_bp.route("/", endpoint="list")
    @role_required("admin", "coach")
    def players_list():
        players, active_condition_count = filter_players(request.args)
        return render_template(
            "players/list.html",
            players=players,
            total_count=len(PLAYERS),
            active_condition_count=active_condition_count,
            logic=request.args.get("logic", "and"),
        )

    @players_bp.route("/create", endpoint="create")
    @role_required("admin")
    def players_create():
        return module_page("新增运动员", "建立运动员基础档案，并同步纳入队伍训练管理体系。")

    @players_bp.route("/<int:player_id>/edit", endpoint="edit")
    @role_required("admin")
    def players_edit(player_id):
        return module_page("编辑运动员", f"维护编号 {player_id} 运动员的档案信息、竞技特征和健康状态。")

    training_bp = Blueprint("training", __name__, url_prefix="/training")

    @training_bp.route("/plans", endpoint="plans")
    @role_required("admin", "coach")
    def training_plans():
        return module_page("训练计划管理", "制定、跟踪和复盘运动员训练计划。")

    @training_bp.route("/batch-import", methods=["GET", "POST"], endpoint="batch_import")
    @role_required("admin", "coach")
    def training_batch_import():
        if request.method == "POST":
            flash("训练记录已提交。", "success")
            return redirect(url_for("training.batch_import"))
        return render_template("training/batch_import.html")

    @training_bp.route("/import-excel", methods=["POST"], endpoint="import_excel")
    @role_required("admin", "coach")
    def training_import_excel():
        file = request.files.get("training_excel")
        if not file:
            flash("请先选择 Excel 文件。", "warning")
        else:
            flash(f"已收到文件：{file.filename}，系统将执行数据校验。", "success")
        return redirect(url_for("training.batch_import"))

    injuries_bp = Blueprint("injuries", __name__, url_prefix="/injuries")

    @injuries_bp.route("/", endpoint="list")
    @role_required("admin", "coach")
    def injuries_list():
        return module_page("伤病记录管理", "维护运动员伤病档案，辅助教练组进行训练风险控制。")

    @injuries_bp.route("/player/<int:player_id>/history", endpoint="history")
    @role_required("admin", "coach")
    def injuries_history(player_id):
        return module_page("历史伤病", f"查看编号 {player_id} 运动员的伤病历史、恢复过程和复训记录。")

    fitness_bp = Blueprint("fitness", __name__, url_prefix="/fitness")

    @fitness_bp.route("/tests", endpoint="tests")
    @role_required("admin", "coach")
    def fitness_tests():
        return module_page("体能测试评估", "管理体能测试指标，形成阶段性能力评估。")

    rehab_bp = Blueprint("rehab", __name__, url_prefix="/rehab")

    @rehab_bp.route("/", endpoint="list")
    @role_required("admin", "coach")
    def rehab_list():
        return module_page("康复跟踪预警", "跟踪伤病康复进度，识别复训风险。")

    matches_bp = Blueprint("matches", __name__, url_prefix="/matches")

    @matches_bp.route("/", endpoint="list")
    @role_required("admin", "coach")
    def matches_list():
        return module_page("比赛成绩报告", "沉淀比赛成绩、技战术复盘和阶段报告。")

    auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

    @auth_bp.route("/users", endpoint="users")
    @role_required("admin")
    def auth_users():
        users = [
            {"username": username, **user}
            for username, user in USERS.items()
        ]
        return render_template("auth/users.html", users=users)

    settings_bp = Blueprint("settings", __name__, url_prefix="/settings")

    @settings_bp.route("/dictionary", endpoint="dictionary")
    @role_required("admin")
    def settings_dictionary():
        return module_page("系统配置", "维护系统基础参数、数据字典和导入模板规则。")

    app.register_blueprint(players_bp)
    app.register_blueprint(training_bp)
    app.register_blueprint(injuries_bp)
    app.register_blueprint(fitness_bp)
    app.register_blueprint(rehab_bp)
    app.register_blueprint(matches_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(settings_bp)

    return app


def filter_players(args):
    logic = args.get("logic", "and")
    predicates = []

    student_no = args.get("student_no", "").strip()
    name = args.get("name", "").strip()
    gender = args.get("gender", "").strip()
    level = args.get("level", "").strip()
    play_style = args.get("play_style", "").strip()
    injury_status = args.get("injury_status", "").strip()
    age_min = args.get("age_min", "").strip()
    age_max = args.get("age_max", "").strip()

    if student_no:
        predicates.append(lambda player, value=student_no: value in player["student_no"])
    if name:
        predicates.append(lambda player, value=name: value.lower() in player["name"].lower())
    if gender:
        predicates.append(lambda player, value=gender: player["gender"] == value)
    if level:
        predicates.append(lambda player, value=level: player["level_code"] == value)
    if play_style:
        predicates.append(lambda player, value=play_style: value.lower() in player["play_style"].lower())
    if injury_status:
        predicates.append(lambda player, value=injury_status: player["injury_status_code"] == value)
    if age_min.isdigit():
        predicates.append(lambda player, value=int(age_min): player["age"] >= value)
    if age_max.isdigit():
        predicates.append(lambda player, value=int(age_max): player["age"] <= value)

    if not predicates:
        return PLAYERS, 0

    if logic == "or":
        return [player for player in PLAYERS if any(check(player) for check in predicates)], len(predicates)

    return [player for player in PLAYERS if all(check(player) for check in predicates)], len(predicates)


def current_user():
    username = session.get("username")
    if not username:
        return None
    user = USERS.get(username)
    if not user:
        return None
    return {"username": username, **user}


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


def module_page(module_name, module_desc):
    return render_template(
        "module_overview.html",
        module_name=module_name,
        module_desc=module_desc,
        features=MODULE_FEATURES.get(module_name, []),
    )


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
