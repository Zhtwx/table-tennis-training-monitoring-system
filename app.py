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

# 认证与权限工具（共享模块）
from auth_utils import USERS, current_user, role_required

# 导入运动员信息管理模块 Blueprint
from players import players_bp


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
        "skill_level": "一级运动员",
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
        "skill_level": "二级运动员",
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
        "skill_level": "国家级",
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
        "skill_level": "一级运动员",
        "level_code": "first",
        "play_style": "右手横板反手快拨",
        "injury_status": "伤病中",
        "injury_status_code": "injured",
    },
]

COACHES = [
    {"id": 1, "name": "陈指导", "specialty": "技术训练"},
    {"id": 2, "name": "刘指导", "specialty": "体能训练"},
    {"id": 3, "name": "马指导", "specialty": "战术分析"},
]

FITNESS_TESTS = [
    {
        "id": 1,
        "athlete_id": 1,
        "test_date": "2026-06-03",
        "tester_id": 2,
        "upper_strength": 84.0,
        "lower_strength": 88.0,
        "flexibility": 82.0,
        "endurance": 86.0,
        "speed": 91.0,
        "overall_score": 86.2,
        "notes": "训练状态稳定，体能结构均衡。",
        "created_by": "coach",
    },
    {
        "id": 2,
        "athlete_id": 2,
        "test_date": "2026-06-11",
        "tester_id": 2,
        "upper_strength": 76.0,
        "lower_strength": 78.0,
        "flexibility": 74.0,
        "endurance": 79.0,
        "speed": 73.0,
        "overall_score": 76.0,
        "notes": "速度指标偏低，建议增加敏捷与启动练习。",
        "created_by": "coach",
    },
    {
        "id": 3,
        "athlete_id": 3,
        "test_date": "2026-06-18",
        "tester_id": 2,
        "upper_strength": 82.0,
        "lower_strength": 84.0,
        "flexibility": 68.0,
        "endurance": 81.0,
        "speed": 76.0,
        "overall_score": 78.2,
        "notes": "柔韧性偏低，需加强拉伸和恢复。",
        "created_by": "admin",
    },
    {
        "id": 4,
        "athlete_id": 4,
        "test_date": "2026-07-02",
        "tester_id": 2,
        "upper_strength": 70.0,
        "lower_strength": 66.0,
        "flexibility": 58.0,
        "endurance": 69.0,
        "speed": 64.0,
        "overall_score": 65.4,
        "notes": "恢复期指标偏弱，维持低强度过渡方案。",
        "created_by": "coach",
    },
]

TRAINING_SYNC_LOGS = [
    {
        "id": 1,
        "fitness_test_id": 1,
        "athlete_id": 1,
        "coach_id": 2,
        "sync_date": "2026-06-03",
        "plan_name": "体能巩固训练",
        "hours": 16.0,
        "intensity": "中",
        "status": "已完成",
    },
    {
        "id": 2,
        "fitness_test_id": 2,
        "athlete_id": 2,
        "coach_id": 2,
        "sync_date": "2026-06-11",
        "plan_name": "速度敏捷提升",
        "hours": 18.0,
        "intensity": "中",
        "status": "已完成",
    },
    {
        "id": 3,
        "fitness_test_id": 3,
        "athlete_id": 3,
        "coach_id": 2,
        "sync_date": "2026-06-18",
        "plan_name": "恢复拉伸结合耐力课",
        "hours": 20.0,
        "intensity": "高",
        "status": "进行中",
    },
    {
        "id": 4,
        "fitness_test_id": 4,
        "athlete_id": 4,
        "coach_id": 2,
        "sync_date": "2026-07-02",
        "plan_name": "康复过渡训练",
        "hours": 12.0,
        "intensity": "低",
        "status": "进行中",
    },
]

INTENSITY_LABELS = {
    "低": "低",
    "中": "中",
    "高": "高",
    "极高": "极高",
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

    # 运动员信息管理模块已在 players.py 中定义，此处直接注册
    app.register_blueprint(players_bp)

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
            athlete_choices=PLAYERS,
            coach_choices=COACHES,
            summary=summary,
            risk_options=[
                {"code": "stable", "label": "稳定"},
                {"code": "observe", "label": "观察"},
                {"code": "alert", "label": "预警"},
            ],
            intensity_options=INTENSITY_LABELS,
            plan_status_options=["进行中", "已完成", "已取消"],
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
    score_min = args.get("score_min", "").strip()
    lower_strength_min = args.get("lower_strength_min", "").strip()
    speed_min = args.get("speed_min", "").strip()

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
        predicates.append(lambda record, value=intensity: record["plan_intensity"] == value)
    if is_float_value(score_min):
        predicates.append(lambda record, value=float(score_min): record["overall_score"] >= value)
    if is_float_value(lower_strength_min):
        predicates.append(lambda record, value=float(lower_strength_min): record["lower_strength"] >= value)
    if is_float_value(speed_min):
        predicates.append(lambda record, value=float(speed_min): record["speed"] >= value)

    records = [enrich_fitness_record(item) for item in FITNESS_TESTS]
    records.sort(key=lambda item: (item["test_date"], item["id"]), reverse=True)
    if not predicates:
        return records, 0
    filtered = [record for record in records if all(check(record) for check in predicates)]
    return filtered, len(predicates)


def enrich_fitness_record(record):
    player = next((item for item in PLAYERS if item["id"] == record["athlete_id"]), None)
    coach = next((item for item in COACHES if item["id"] == record["tester_id"]), None)
    sync_plan = next((item for item in TRAINING_SYNC_LOGS if item["fitness_test_id"] == record["id"]), None)
    risk = evaluate_fitness_risk(record)
    score = calculate_fitness_score(record)
    upper_strength_status = classify_metric_status(record["upper_strength"], 70, 80, lower_is_worse=True)
    lower_strength_status = classify_metric_status(record["lower_strength"], 70, 80, lower_is_worse=True)
    flexibility_status = classify_metric_status(record["flexibility"], 70, 80, lower_is_worse=True)
    endurance_status = classify_metric_status(record["endurance"], 75, 85, lower_is_worse=True)
    speed_status = classify_metric_status(record["speed"], 75, 85, lower_is_worse=True)
    base = dict(record)
    base.update(
        {
            "player_name": player["name"] if player else "未知运动员",
            "student_no": player["student_no"] if player else "-",
            "level": (player.get("skill_level") or player.get("level")) if player else "-",
            "tester_name": coach["name"] if coach else "未指定",
            "risk_code": risk["code"],
            "risk_label": risk["label"],
            "risk_class": risk["class"],
            "fitness_score": score,
            "upper_strength_status": upper_strength_status,
            "lower_strength_status": lower_strength_status,
            "flexibility_status": flexibility_status,
            "endurance_status": endurance_status,
            "speed_status": speed_status,
            "plan_name": sync_plan["plan_name"] if sync_plan else "-",
            "plan_hours": sync_plan["hours"] if sync_plan else 0,
            "plan_intensity": sync_plan["intensity"] if sync_plan else "",
            "plan_status": sync_plan["status"] if sync_plan else "-",
        }
    )
    return base


def evaluate_fitness_risk(record):
    alerts = 0
    observes = 0
    if record["upper_strength"] < 70:
        alerts += 1
    elif record["upper_strength"] < 80:
        observes += 1
    if record["lower_strength"] < 70:
        alerts += 1
    elif record["lower_strength"] < 80:
        observes += 1
    if record["flexibility"] < 70:
        alerts += 1
    elif record["flexibility"] < 80:
        observes += 1
    if record["endurance"] < 75:
        alerts += 1
    elif record["endurance"] < 85:
        observes += 1
    if record["speed"] < 75:
        alerts += 1
    elif record["speed"] < 85:
        observes += 1
    if alerts >= 2:
        return {"code": "alert", "label": "预警", "class": "danger"}
    if alerts == 1 or observes >= 2:
        return {"code": "observe", "label": "观察", "class": "warning"}
    return {"code": "stable", "label": "稳定", "class": "success"}


def calculate_fitness_score(record):
    score = (
        record["upper_strength"]
        + record["lower_strength"]
        + record["flexibility"]
        + record["endurance"]
        + record["speed"]
    ) / 5
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
            {"score_total": 0.0, "speed_total": 0.0, "hours_total": 0.0, "count": 0},
        )
        monthly_stats["score_total"] += record["fitness_score"]
        monthly_stats["speed_total"] += record["speed"]
        monthly_stats["hours_total"] += record["plan_hours"]
        monthly_stats["count"] += 1

        player_stats = player_map.setdefault(record["player_name"], {"score_total": 0.0, "count": 0})
        player_stats["score_total"] += record["fitness_score"]
        player_stats["count"] += 1

    month_labels = sorted(monthly_map.keys())
    monthly_scores = [round(monthly_map[key]["score_total"] / monthly_map[key]["count"], 1) for key in month_labels]
    monthly_speed = [round(monthly_map[key]["speed_total"] / monthly_map[key]["count"], 1) for key in month_labels]
    monthly_hours = [round(monthly_map[key]["hours_total"], 1) for key in month_labels]

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
        "avg_speed": round(sum(record["speed"] for record in records) / len(records), 1) if records else 0,
        "risk_pie": [{"name": key, "value": value} for key, value in risk_counts.items()],
        "month_labels": month_labels,
        "monthly_scores": monthly_scores,
        "monthly_speed": monthly_speed,
        "monthly_hours": monthly_hours,
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
                        "athlete_id": validated["athlete_id"],
                        "coach_id": validated["tester_id"],
                        "sync_date": validated["test_date"],
                        "plan_name": validated["plan_name"],
                        "hours": validated["hours"],
                        "intensity": validated["intensity"],
                        "status": validated["plan_status"],
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
                    "athlete_id": validated["athlete_id"],
                    "coach_id": validated["tester_id"],
                    "sync_date": validated["test_date"],
                    "plan_name": validated["plan_name"],
                    "hours": validated["hours"],
                    "intensity": validated["intensity"],
                    "status": validated["plan_status"],
                }
            )
    except Exception:
        FITNESS_TESTS[:] = original_tests
        TRAINING_SYNC_LOGS[:] = original_logs
        raise


def validate_fitness_form(form):
    record_id = form.get("record_id", "").strip()
    athlete_id = parse_int_field(form.get("athlete_id", "").strip(), "运动员")
    if not any(player["id"] == athlete_id for player in PLAYERS):
        raise ValidationError("所选运动员不存在，请重新选择。")
    tester_id = parse_int_field(form.get("tester_id", "").strip(), "测试教练")
    if not any(coach["id"] == tester_id for coach in COACHES):
        raise ValidationError("所选测试教练不存在，请重新选择。")

    test_date = form.get("test_date", "").strip()
    try:
        datetime.strptime(test_date, "%Y-%m-%d")
    except ValueError as exc:
        raise ValidationError("测试日期格式错误，请使用 YYYY-MM-DD。") from exc

    upper_strength = parse_float_range(form.get("upper_strength", "").strip(), "上肢力量", 0, 100)
    lower_strength = parse_float_range(form.get("lower_strength", "").strip(), "下肢力量", 0, 100)
    flexibility = parse_float_range(form.get("flexibility", "").strip(), "柔韧性", 0, 100)
    endurance = parse_float_range(form.get("endurance", "").strip(), "耐力", 0, 100)
    speed = parse_float_range(form.get("speed", "").strip(), "速度", 0, 100)
    hours = parse_float_range(form.get("hours", "").strip(), "训练时长", 0, 999.9)

    intensity = form.get("intensity", "").strip()
    if intensity not in INTENSITY_LABELS:
        raise ValidationError("训练强度非法，请从低、中、高、极高中选择。")
    plan_status = form.get("plan_status", "").strip()
    if plan_status not in {"进行中", "已完成", "已取消"}:
        raise ValidationError("训练计划状态非法。")
    plan_name = form.get("plan_name", "").strip()
    if not plan_name:
        raise ValidationError("训练计划名称不能为空。")

    notes = form.get("notes", "").strip()
    if len(notes) > 120:
        raise ValidationError("备注不能超过 120 个字符。")

    overall_score = round((upper_strength + lower_strength + flexibility + endurance + speed) / 5, 2)

    return {
        "record_id": int(record_id) if record_id.isdigit() else None,
        "athlete_id": athlete_id,
        "test_date": test_date,
        "tester_id": tester_id,
        "upper_strength": upper_strength,
        "lower_strength": lower_strength,
        "flexibility": flexibility,
        "endurance": endurance,
        "speed": speed,
        "overall_score": overall_score,
        "plan_name": plan_name,
        "hours": hours,
        "intensity": intensity,
        "plan_status": plan_status,
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
