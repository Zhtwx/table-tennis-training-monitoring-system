from pymysql import MySQLError
from flask import flash, redirect, render_template, request, url_for

from db import get_mysql_connection
from . import bp


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


@bp.route("/", endpoint="list")
def list_coaches():
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
        flash(f"教练员数据暂时不可用：{exc}", "warning")
        coaches = []
    return render_template("coaches/list.html", coaches=coaches)


@bp.route("/add", methods=["GET", "POST"])
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
            flash(f"保存失败：{exc}", "danger")

    return render_template("coaches/form.html", coach=None)


@bp.route("/edit/<int:id>", methods=["GET", "POST"])
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
        flash(f"读取教练员信息失败：{exc}", "danger")
        return redirect(url_for("coaches.list"))

    if not coach:
        flash("教练员不存在。", "warning")
        return redirect(url_for("coaches.list"))

    return render_template("coaches/form.html", coach=coach)


@bp.route("/delete/<int:id>", methods=["POST"])
def delete_coach(id):
    try:
        result = fetch_one("SELECT COUNT(*) AS total FROM training_plan WHERE coach_id=%s", (id,))
        if result and result["total"] > 0:
            flash("该教练员已有训练计划记录，无法删除。", "danger")
            return redirect(url_for("coaches.list"))

        execute_write("DELETE FROM coach WHERE id=%s", (id,))
        flash("教练员已删除。", "success")
    except MySQLError as exc:
        flash(f"删除失败：{exc}", "danger")

    return redirect(url_for("coaches.list"))


@bp.route("/<int:id>/players")
def coach_players(id):
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
        flash(f"队员数据暂时不可用：{exc}", "warning")
        return redirect(url_for("coaches.list"))

    return render_template("coaches/players.html", coach=coach, players=players)
