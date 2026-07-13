from datetime import date

from flask import flash, redirect, render_template, request, url_for
from pymysql import MySQLError

from auth_utils import role_required
from db import get_mysql_connection
from . import bp


DATABASE_SETUP_ERROR_CODES = {1045, 1049, 1146, 2002, 2003, 2005, 2006}

FALLBACK_COACHES = [
    {
        "id": 1,
        "name": "张教练",
        "gender": "男",
        "phone": "13800000001",
        "email": "zhang.coach@example.com",
        "specialty": "乒乓球专项训练",
        "hire_date": "2026-07-01",
    },
    {
        "id": 2,
        "name": "李教练",
        "gender": "女",
        "phone": "13800000002",
        "email": "li.coach@example.com",
        "specialty": "体能训练与康复",
        "hire_date": "2026-07-02",
    },
]

FALLBACK_PLAYERS = [
    {
        "id": 1,
        "name": "王一鸣",
        "gender": "男",
        "birth_date": "2007-03-10",
        "team": "一队",
        "skill_level": "一级运动员",
    },
    {
        "id": 2,
        "name": "李清扬",
        "gender": "女",
        "birth_date": "2008-05-21",
        "team": "一队",
        "skill_level": "二级运动员",
    },
]

FALLBACK_TRAINING_PLANS = [
    {"athlete_id": 1, "coach_id": 1, "start_date": "2026-07-01"},
    {"athlete_id": 2, "coach_id": 2, "start_date": "2026-07-02"},
]

GENDER_OPTIONS = ["男", "女"]
PLAYER_LEVEL_OPTIONS = ["二级运动员", "一级运动员", "国家级", "健将级", "青年队"]


def fetch_all(query, params=None):
    connection = get_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()
    finally:
        connection.close()


def fetch_one(query, params=None):
    connection = get_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchone()
    finally:
        connection.close()


def execute_write(query, params=None):
    connection = get_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params or ())
        connection.commit()
    except MySQLError:
        connection.rollback()
        raise
    finally:
        connection.close()


def is_database_setup_error(exc):
    code = exc.args[0] if exc.args and isinstance(exc.args[0], int) else None
    return code in DATABASE_SETUP_ERROR_CODES


def fallback_coach_rows():
    rows = []
    for coach in FALLBACK_COACHES:
        assignments = [
            plan for plan in FALLBACK_TRAINING_PLANS if plan["coach_id"] == coach["id"]
        ]
        row = dict(coach)
        row["player_count"] = len({plan["athlete_id"] for plan in assignments})
        row["latest_training_date"] = max(
            (plan["start_date"] for plan in assignments),
            default=None,
        )
        rows.append(row)
    return sorted(rows, key=lambda item: item["id"], reverse=True)


def fallback_get_coach(coach_id):
    coach = next((item for item in FALLBACK_COACHES if item["id"] == coach_id), None)
    return dict(coach) if coach else None


def fallback_add_coach(form):
    coach_id = max((coach["id"] for coach in FALLBACK_COACHES), default=0) + 1
    FALLBACK_COACHES.append(
        {
            "id": coach_id,
            "name": form["name"],
            "gender": form["gender"],
            "phone": form.get("phone") or None,
            "email": form.get("email") or None,
            "specialty": form.get("specialty") or None,
            "hire_date": date.today().isoformat(),
        }
    )


def fallback_update_coach(coach_id, form):
    coach = next((item for item in FALLBACK_COACHES if item["id"] == coach_id), None)
    if not coach:
        return False
    coach.update(
        {
            "name": form["name"],
            "gender": form["gender"],
            "phone": form.get("phone") or None,
            "email": form.get("email") or None,
            "specialty": form.get("specialty") or None,
        }
    )
    return True


def fallback_delete_coach(coach_id):
    row = next((item for item in fallback_coach_rows() if item["id"] == coach_id), None)
    if not row:
        return "missing"
    if row["player_count"] > 0:
        return "has_players"
    FALLBACK_COACHES[:] = [coach for coach in FALLBACK_COACHES if coach["id"] != coach_id]
    return "deleted"


def fallback_players_for_coach(coach_id):
    rows = []
    for plan in FALLBACK_TRAINING_PLANS:
        if plan["coach_id"] != coach_id:
            continue
        player = next(
            (item for item in FALLBACK_PLAYERS if item["id"] == plan["athlete_id"]),
            None,
        )
        if not player:
            continue
        row = dict(player)
        row["latest_training_date"] = plan["start_date"]
        rows.append(row)
    return sorted(rows, key=lambda item: item["name"])


def normalize_text(value):
    return str(value or "").strip().lower()


def parse_non_negative_int(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = int(text)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


def build_coach_filters(args):
    return {
        "keyword": args.get("keyword", "").strip(),
        "gender": args.get("gender", "").strip(),
        "has_players": args.get("has_players", "").strip(),
        "min_players": parse_non_negative_int(args.get("min_players")),
    }


def build_player_filters(args):
    return {
        "keyword": args.get("keyword", "").strip(),
        "team": args.get("team", "").strip(),
        "gender": args.get("gender", "").strip(),
        "skill_level": args.get("skill_level", "").strip(),
    }


def count_active_filters(filters, keys):
    return sum(1 for key in keys if filters.get(key) not in ("", None))


def coach_matches_filters(coach, filters):
    keyword = normalize_text(filters.get("keyword"))
    if keyword:
        haystack = " ".join(
            normalize_text(coach.get(field)) for field in ("name", "phone", "email", "specialty")
        )
        if keyword not in haystack:
            return False

    if filters.get("gender") and coach.get("gender") != filters["gender"]:
        return False

    player_count = int(coach.get("player_count") or 0)
    if filters.get("has_players") == "yes" and player_count <= 0:
        return False
    if filters.get("has_players") == "no" and player_count > 0:
        return False

    min_players = filters.get("min_players")
    if min_players is not None and player_count < min_players:
        return False

    return True


def player_matches_filters(player, filters):
    keyword = normalize_text(filters.get("keyword"))
    if keyword:
        haystack = " ".join(
            normalize_text(player.get(field))
            for field in ("name", "team", "skill_level")
        )
        if keyword not in haystack:
            return False

    if filters.get("team") and filters["team"] not in normalize_text(player.get("team")):
        return False

    if filters.get("gender") and player.get("gender") != filters["gender"]:
        return False

    if filters.get("skill_level") and player.get("skill_level") != filters["skill_level"]:
        return False

    return True


@bp.route("/", endpoint="list")
def list_coaches():
    filters = build_coach_filters(request.args)
    query = """
        SELECT
            c.id,
            c.name,
            c.gender,
            c.contact_phone AS phone,
            c.email,
            c.specialty,
            c.create_time AS hire_date,
            COUNT(DISTINCT tp.athlete_id) AS player_count,
            MAX(tp.start_date) AS latest_training_date
        FROM coach c
        LEFT JOIN training_plan tp ON c.id = tp.coach_id
        GROUP BY c.id, c.name, c.gender, c.contact_phone, c.email, c.specialty, c.create_time
        ORDER BY c.id DESC
    """
    try:
        coaches = fetch_all(query)
    except MySQLError as exc:
        if is_database_setup_error(exc):
            coaches = fallback_coach_rows()
        else:
            flash(f"教练员数据暂时不可用：{exc}", "warning")
            coaches = []
    total_count = len(coaches)
    coaches = [coach for coach in coaches if coach_matches_filters(coach, filters)]
    active_condition_count = count_active_filters(filters, ("keyword", "gender", "has_players", "min_players"))
    return render_template(
        "coaches/list.html",
        coaches=coaches,
        total_count=total_count,
        active_condition_count=active_condition_count,
        gender_options=GENDER_OPTIONS,
    )


@bp.route("/add", methods=["GET", "POST"])
@role_required("admin")
def add_coach():
    if request.method == "POST":
        query = """
            INSERT INTO coach (name, gender, contact_phone, email, specialty)
            VALUES (%s, %s, %s, %s, %s)
        """
        params = (
            request.form["name"],
            request.form["gender"],
            request.form.get("phone") or None,
            request.form.get("email") or None,
            request.form.get("specialty") or None,
        )
        try:
            execute_write(query, params)
            flash("教练员添加成功。", "success")
            return redirect(url_for("coaches.list"))
        except MySQLError as exc:
            if is_database_setup_error(exc):
                fallback_add_coach(request.form)
                flash("教练员已保存到本地示例数据。", "success")
                return redirect(url_for("coaches.list"))
            flash(f"保存失败：{exc}", "danger")

    return render_template("coaches/form.html", coach=None)


@bp.route("/edit/<int:id>", methods=["GET", "POST"])
@role_required("admin")
def edit_coach(id):
    if request.method == "POST":
        query = """
            UPDATE coach
            SET name=%s, gender=%s, contact_phone=%s, email=%s, specialty=%s
            WHERE id=%s
        """
        params = (
            request.form["name"],
            request.form["gender"],
            request.form.get("phone") or None,
            request.form.get("email") or None,
            request.form.get("specialty") or None,
            id,
        )
        try:
            execute_write(query, params)
            flash("教练员信息已更新。", "success")
            return redirect(url_for("coaches.list"))
        except MySQLError as exc:
            if is_database_setup_error(exc):
                if fallback_update_coach(id, request.form):
                    flash("教练员信息已更新到本地示例数据。", "success")
                    return redirect(url_for("coaches.list"))
                flash("教练员不存在。", "warning")
                return redirect(url_for("coaches.list"))
            flash(f"更新失败：{exc}", "danger")

    try:
        coach = fetch_one(
            """
            SELECT
                id,
                name,
                gender,
                contact_phone AS phone,
                email,
                specialty,
                create_time AS hire_date
            FROM coach
            WHERE id=%s
            """,
            (id,),
        )
    except MySQLError as exc:
        if is_database_setup_error(exc):
            coach = fallback_get_coach(id)
        else:
            flash(f"读取教练员信息失败：{exc}", "danger")
            return redirect(url_for("coaches.list"))

    if not coach:
        flash("教练员不存在。", "warning")
        return redirect(url_for("coaches.list"))

    return render_template("coaches/form.html", coach=coach)


@bp.route("/delete/<int:id>", methods=["POST"])
@role_required("admin")
def delete_coach(id):
    try:
        result = fetch_one("SELECT COUNT(*) AS total FROM training_plan WHERE coach_id=%s", (id,))
        if result and result["total"] > 0:
            flash("该教练员已有训练计划记录，无法删除。", "danger")
            return redirect(url_for("coaches.list"))

        execute_write("DELETE FROM coach WHERE id=%s", (id,))
        flash("教练员已删除。", "success")
    except MySQLError as exc:
        if is_database_setup_error(exc):
            result = fallback_delete_coach(id)
            if result == "deleted":
                flash("教练员已从本地示例数据删除。", "success")
            elif result == "has_players":
                flash("该教练员已有训练计划记录，无法删除。", "danger")
            else:
                flash("教练员不存在。", "warning")
        else:
            flash(f"删除失败：{exc}", "danger")

    return redirect(url_for("coaches.list"))


@bp.route("/<int:id>/players")
def coach_players(id):
    filters = build_player_filters(request.args)
    try:
        coach = fetch_one("SELECT id, name FROM coach WHERE id=%s", (id,))
        if not coach:
            flash("教练员不存在。", "warning")
            return redirect(url_for("coaches.list"))

        players = fetch_all(
            """
            SELECT
                a.id,
                a.name,
                a.gender,
                a.birth_date,
                a.team,
                a.skill_level,
                MAX(tp.start_date) AS latest_training_date
            FROM athlete a
            JOIN training_plan tp ON a.id = tp.athlete_id
            WHERE tp.coach_id = %s
            GROUP BY a.id, a.name, a.gender, a.birth_date, a.team, a.skill_level
            ORDER BY a.name
            """,
            (id,),
        )
    except MySQLError as exc:
        if is_database_setup_error(exc):
            coach = fallback_get_coach(id)
            if not coach:
                flash("教练员不存在。", "warning")
                return redirect(url_for("coaches.list"))
            players = fallback_players_for_coach(id)
        else:
            flash(f"队员数据暂时不可用：{exc}", "warning")
            return redirect(url_for("coaches.list"))

    total_count = len(players)
    players = [player for player in players if player_matches_filters(player, filters)]
    active_condition_count = count_active_filters(filters, ("keyword", "team", "gender", "skill_level"))
    return render_template(
        "coaches/players.html",
        coach=coach,
        players=players,
        total_count=total_count,
        active_condition_count=active_condition_count,
        gender_options=GENDER_OPTIONS,
        skill_level_options=PLAYER_LEVEL_OPTIONS,
    )
