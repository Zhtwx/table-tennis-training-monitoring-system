from copy import deepcopy
from datetime import datetime
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

FITNESS_TESTS = [
    {
        "id": 1,
        "player_id": 1,
        "test_date": "2026-06-03",
        "lower_limb_strength": 186.0,
        "mobility": 84.0,
        "vertical_jump": 61.0,
        "reaction_time": 0.31,
        "training_duration": 95,
        "training_intensity": "medium",
        "training_intensity_label": "中",
        "notes": "训练状态稳定，起跳爆发力保持良好。",
        "created_by": "coach",
    },
    {
        "id": 2,
        "player_id": 2,
        "test_date": "2026-06-11",
        "lower_limb_strength": 158.0,
        "mobility": 76.0,
        "vertical_jump": 52.0,
        "reaction_time": 0.35,
        "training_duration": 88,
        "training_intensity": "medium",
        "training_intensity_label": "中",
        "notes": "反应速度略有下降，建议控制多球训练总量。",
        "created_by": "coach",
    },
    {
        "id": 3,
        "player_id": 3,
        "test_date": "2026-06-18",
        "lower_limb_strength": 172.0,
        "mobility": 68.0,
        "vertical_jump": 48.0,
        "reaction_time": 0.4,
        "training_duration": 105,
        "training_intensity": "high",
        "training_intensity_label": "高",
        "notes": "关节活动度偏低，安排恢复性训练。",
        "created_by": "admin",
    },
    {
        "id": 4,
        "player_id": 4,
        "test_date": "2026-07-02",
        "lower_limb_strength": 136.0,
        "mobility": 59.0,
        "vertical_jump": 43.0,
        "reaction_time": 0.45,
        "training_duration": 72,
        "training_intensity": "low",
        "training_intensity_label": "低",
        "notes": "伤病恢复阶段，采用低强度过渡方案。",
        "created_by": "coach",
    },
]

TRAINING_SYNC_LOGS = [
    {
        "id": 1,
        "fitness_test_id": 1,
        "player_id": 1,
        "sync_date": "2026-06-03",
        "training_duration": 95,
        "training_intensity": "medium",
    },
    {
        "id": 2,
        "fitness_test_id": 2,
        "player_id": 2,
        "sync_date": "2026-06-11",
        "training_duration": 88,
        "training_intensity": "medium",
    },
    {
        "id": 3,
        "fitness_test_id": 3,
        "player_id": 3,
        "sync_date": "2026-06-18",
        "training_duration": 105,
        "training_intensity": "high",
    },
    {
        "id": 4,
        "fitness_test_id": 4,
        "player_id": 4,
        "sync_date": "2026-07-02",
        "training_duration": 72,
        "training_intensity": "low",
    },
]

INTENSITY_LABELS = {
    "low": "低",
    "medium": "中",
    "high": "高",
}

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

    @fitness_bp.route("/tests", methods=["GET", "POST"], endpoint="tests")
    @role_required("admin", "coach")
    def fitness_tests():
        if request.method == "POST":
            try:
                save_fitness_test(request.form, current_user()["username"])
                flash("体能测试记录已提交，训练数据已与体能数据同步写入。", "success")
            except ValidationError as exc:
                flash(str(exc), "warning")
            except RuntimeError as exc:
                flash(f"事务已回滚：{exc}", "danger")
            return redirect(url_for("fitness.tests", **build_redirect_query(request.form)))

        fitness_records, active_condition_count = filter_fitness_tests(request.args)
        editing_record = get_editing_fitness_record(request.args.get("edit_id", "").strip())
        summary = build_fitness_summary(fitness_records)
        return render_template(
            "fitness/tests.html",
            fitness_records=fitness_records,
            active_condition_count=active_condition_count,
            total_count=len(FITNESS_TESTS),
            editing_record=editing_record,
            player_choices=PLAYERS,
            summary=summary,
            risk_options=[
                {"code": "stable", "label": "稳定"},
                {"code": "observe", "label": "观察"},
                {"code": "alert", "label": "预警"},
            ],
            intensity_options=INTENSITY_LABELS,
        )

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


class ValidationError(Exception):
    pass


def filter_fitness_tests(args):
    predicates = []
    player_keyword = args.get("player_keyword", "").strip().lower()
    date_from = args.get("date_from", "").strip()
    date_to = args.get("date_to", "").strip()
    risk_level = args.get("risk_level", "").strip()
    intensity = args.get("intensity", "").strip()
    reaction_max = args.get("reaction_max", "").strip()
    jump_min = args.get("jump_min", "").strip()

    if player_keyword:
        predicates.append(
            lambda record, value=player_keyword: value in record["player_name"].lower()
            or value in record["student_no"].lower()
        )
    if date_from:
        predicates.append(lambda record, value=date_from: record["test_date"] >= value)
    if date_to:
        predicates.append(lambda record, value=date_to: record["test_date"] <= value)
    if risk_level:
        predicates.append(lambda record, value=risk_level: record["risk_code"] == value)
    if intensity:
        predicates.append(lambda record, value=intensity: record["training_intensity"] == value)
    if is_float_value(reaction_max):
        predicates.append(lambda record, value=float(reaction_max): record["reaction_time"] <= value)
    if is_float_value(jump_min):
        predicates.append(lambda record, value=float(jump_min): record["vertical_jump"] >= value)

    records = [enrich_fitness_record(item) for item in FITNESS_TESTS]
    records.sort(key=lambda item: (item["test_date"], item["id"]), reverse=True)
    if not predicates:
        return records, 0
    filtered = [record for record in records if all(check(record) for check in predicates)]
    return filtered, len(predicates)


def enrich_fitness_record(record):
    player = next((item for item in PLAYERS if item["id"] == record["player_id"]), None)
    risk = evaluate_fitness_risk(record)
    score = calculate_fitness_score(record)
    strength_status = classify_metric_status(record["lower_limb_strength"], 150, 170, lower_is_worse=True)
    mobility_status = classify_metric_status(record["mobility"], 60, 75, lower_is_worse=True)
    jump_status = classify_metric_status(record["vertical_jump"], 45, 55, lower_is_worse=True)
    reaction_status = classify_metric_status(record["reaction_time"], 0.40, 0.35, lower_is_worse=False)
    base = dict(record)
    base.update(
        {
            "player_name": player["name"] if player else "未知运动员",
            "student_no": player["student_no"] if player else "-",
            "level": player["level"] if player else "-",
            "risk_code": risk["code"],
            "risk_label": risk["label"],
            "risk_class": risk["class"],
            "fitness_score": score,
            "strength_status": strength_status,
            "mobility_status": mobility_status,
            "jump_status": jump_status,
            "reaction_status": reaction_status,
        }
    )
    return base


def evaluate_fitness_risk(record):
    alerts = 0
    observes = 0
    if record["lower_limb_strength"] < 150:
        alerts += 1
    elif record["lower_limb_strength"] < 170:
        observes += 1
    if record["mobility"] < 60:
        alerts += 1
    elif record["mobility"] < 75:
        observes += 1
    if record["vertical_jump"] < 45:
        alerts += 1
    elif record["vertical_jump"] < 55:
        observes += 1
    if record["reaction_time"] > 0.4:
        alerts += 1
    elif record["reaction_time"] > 0.34:
        observes += 1
    if alerts >= 2:
        return {"code": "alert", "label": "预警", "class": "danger"}
    if alerts == 1 or observes >= 2:
        return {"code": "observe", "label": "观察", "class": "warning"}
    return {"code": "stable", "label": "稳定", "class": "success"}


def calculate_fitness_score(record):
    strength = min(record["lower_limb_strength"] / 200 * 100, 100)
    mobility = min(record["mobility"], 100)
    jump = min(record["vertical_jump"] / 65 * 100, 100)
    reaction = max(0, min((0.5 - record["reaction_time"]) / 0.3 * 100, 100))
    score = strength * 0.28 + mobility * 0.22 + jump * 0.28 + reaction * 0.22
    return round(score, 1)


def classify_metric_status(value, alert_threshold, observe_threshold, *, lower_is_worse):
    if lower_is_worse:
        if value < alert_threshold:
            return "alert"
        if value < observe_threshold:
            return "observe"
        return "normal"
    if value > alert_threshold:
        return "alert"
    if value > observe_threshold:
        return "observe"
    return "normal"


def build_fitness_summary(records):
    risk_counts = {"稳定": 0, "观察": 0, "预警": 0}
    monthly_map = {}
    player_map = {}
    for record in records:
        risk_counts[record["risk_label"]] += 1
        month_key = record["test_date"][:7]
        monthly_stats = monthly_map.setdefault(
            month_key,
            {"jump_total": 0.0, "reaction_total": 0.0, "duration_total": 0, "count": 0},
        )
        monthly_stats["jump_total"] += record["vertical_jump"]
        monthly_stats["reaction_total"] += record["reaction_time"]
        monthly_stats["duration_total"] += record["training_duration"]
        monthly_stats["count"] += 1

        player_stats = player_map.setdefault(record["player_name"], {"score_total": 0.0, "count": 0})
        player_stats["score_total"] += record["fitness_score"]
        player_stats["count"] += 1

    month_labels = sorted(monthly_map.keys())
    monthly_jump = [round(monthly_map[key]["jump_total"] / monthly_map[key]["count"], 1) for key in month_labels]
    monthly_reaction = [round(monthly_map[key]["reaction_total"] / monthly_map[key]["count"], 3) for key in month_labels]
    monthly_duration = [monthly_map[key]["duration_total"] for key in month_labels]

    player_scores = sorted(
        (
            {
                "name": name,
                "score": round(stats["score_total"] / stats["count"], 1),
            }
            for name, stats in player_map.items()
        ),
        key=lambda item: item["score"],
        reverse=True,
    )

    return {
        "record_count": len(records),
        "warning_count": risk_counts["预警"],
        "average_score": round(sum(record["fitness_score"] for record in records) / len(records), 1) if records else 0,
        "avg_reaction": round(sum(record["reaction_time"] for record in records) / len(records), 3) if records else 0,
        "risk_pie": [{"name": key, "value": value} for key, value in risk_counts.items()],
        "month_labels": month_labels,
        "monthly_jump": monthly_jump,
        "monthly_reaction": monthly_reaction,
        "monthly_duration": monthly_duration,
        "player_names": [item["name"] for item in player_scores],
        "player_scores": [item["score"] for item in player_scores],
    }


def get_editing_fitness_record(edit_id):
    if not edit_id.isdigit():
        return None
    record = next((item for item in FITNESS_TESTS if item["id"] == int(edit_id)), None)
    return enrich_fitness_record(record) if record else None


def save_fitness_test(form, operator):
    validated = validate_fitness_form(form)
    simulate_failure = form.get("simulate_failure") == "1"
    original_tests = deepcopy(FITNESS_TESTS)
    original_logs = deepcopy(TRAINING_SYNC_LOGS)
    try:
        record_id = validated.pop("record_id")
        if record_id:
            target = next((item for item in FITNESS_TESTS if item["id"] == record_id), None)
            if not target:
                raise ValidationError("要修改的体能测试记录不存在。")
            target.update(validated)
            target["created_by"] = operator
            sync_log = next((item for item in TRAINING_SYNC_LOGS if item["fitness_test_id"] == record_id), None)
            if sync_log:
                sync_log.update(
                    {
                        "player_id": validated["player_id"],
                        "sync_date": validated["test_date"],
                        "training_duration": validated["training_duration"],
                        "training_intensity": validated["training_intensity"],
                    }
                )
        else:
            new_id = next_id(FITNESS_TESTS)
            FITNESS_TESTS.append(
                {
                    "id": new_id,
                    **validated,
                    "created_by": operator,
                }
            )
            TRAINING_SYNC_LOGS.append(
                {
                    "id": next_id(TRAINING_SYNC_LOGS),
                    "fitness_test_id": new_id,
                    "player_id": validated["player_id"],
                    "sync_date": validated["test_date"],
                    "training_duration": validated["training_duration"],
                    "training_intensity": validated["training_intensity"],
                }
            )

        if simulate_failure:
            raise RuntimeError("训练计划写入阶段触发异常，已撤销本次体能测试提交。")
    except Exception:
        FITNESS_TESTS[:] = original_tests
        TRAINING_SYNC_LOGS[:] = original_logs
        raise


def validate_fitness_form(form):
    record_id = form.get("record_id", "").strip()
    player_id = parse_int_field(form.get("player_id", "").strip(), "运动员")
    if not any(player["id"] == player_id for player in PLAYERS):
        raise ValidationError("所选运动员不存在，请重新选择。")

    test_date = form.get("test_date", "").strip()
    try:
        datetime.strptime(test_date, "%Y-%m-%d")
    except ValueError as exc:
        raise ValidationError("测试日期格式错误，请使用 YYYY-MM-DD。") from exc

    lower_limb_strength = parse_float_range(form.get("lower_limb_strength", "").strip(), "下肢力量", 80, 260)
    mobility = parse_float_range(form.get("mobility", "").strip(), "关节活动度", 0, 100)
    vertical_jump = parse_float_range(form.get("vertical_jump", "").strip(), "纵跳高度", 20, 100)
    reaction_time = parse_float_range(form.get("reaction_time", "").strip(), "反应速度", 0.1, 1.2)
    training_duration = parse_int_range(form.get("training_duration", "").strip(), "关联训练时长", 10, 360)

    training_intensity = form.get("training_intensity", "").strip()
    if training_intensity not in INTENSITY_LABELS:
        raise ValidationError("训练强度非法，请从低、中、高中选择。")

    notes = form.get("notes", "").strip()
    if len(notes) > 120:
        raise ValidationError("备注不能超过 120 个字符。")

    return {
        "record_id": int(record_id) if record_id.isdigit() else None,
        "player_id": player_id,
        "test_date": test_date,
        "lower_limb_strength": lower_limb_strength,
        "mobility": mobility,
        "vertical_jump": vertical_jump,
        "reaction_time": reaction_time,
        "training_duration": training_duration,
        "training_intensity": training_intensity,
        "training_intensity_label": INTENSITY_LABELS[training_intensity],
        "notes": notes,
    }


def build_redirect_query(form):
    edit_id = form.get("record_id", "").strip()
    if edit_id:
        return {"edit_id": edit_id}
    return {}


def next_id(rows):
    return max((item["id"] for item in rows), default=0) + 1


def parse_int_field(value, field_name):
    if not value:
        raise ValidationError(f"{field_name}不能为空。")
    try:
        return int(value)
    except ValueError as exc:
        raise ValidationError(f"{field_name}必须为整数。") from exc


def parse_int_range(value, field_name, min_value, max_value):
    parsed = parse_int_field(value, field_name)
    if parsed < min_value or parsed > max_value:
        raise ValidationError(f"{field_name}必须介于 {min_value} 和 {max_value} 之间。")
    return parsed


def parse_float_range(value, field_name, min_value, max_value):
    if not value:
        raise ValidationError(f"{field_name}不能为空。")
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValidationError(f"{field_name}必须为数字类型。") from exc
    if parsed < min_value or parsed > max_value:
        raise ValidationError(f"{field_name}必须介于 {min_value} 和 {max_value} 之间。")
    return round(parsed, 3)


def is_float_value(value):
    if not value:
        return False
    try:
        float(value)
        return True
    except ValueError:
        return False


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
