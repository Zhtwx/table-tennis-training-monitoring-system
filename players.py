# ============================================================
# 乒乓球运动员综合训练监控管理系统 · 运动员信息管理模块
# 模块职责: 运动员档案的增删改查（CRUD）、多条件动态组合查询
# 使用技术: Flask Blueprint + PyMySQL + MySQL
# 作者: [成员姓名]
# 日期: 2026-07-08
# ============================================================
#
# 【模块功能概述】
# 1. 运动员列表查询   - 支持 8 个维度的多条件动态组合筛选（AND/OR 逻辑切换）
# 2. 运动员档案详情   - 展示基本信息 + 统计分析（训练/技术/体能/伤病汇总）
# 3. 新增运动员       - 表单验证 + 唯一性检查 + INSERT
# 4. 编辑运动员       - 数据回填 + 字段校验 + UPDATE
# 5. 删除运动员       - 级联删除（数据库外键 CASCADE 自动处理关联数据）
#
# 【核心技术要点】
# - 动态 WHERE 子句构建：根据用户输入的非空条件动态拼接 SQL
# - 模糊查询：name/student_no/play_style 使用 LIKE %keyword%
# - 范围查询：age 通过 birth_date 计算（YEAR(CURDATE()) - YEAR(birth_date)）
# - 事务支持：增删改操作使用事务保证数据一致性
# - 触发器适配：通过 injury_status 字段与 injury_record 表的触发器联动
# ============================================================

from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from auth_utils import role_required
from db import (
    build_like_pattern,
    build_where_clause,
    execute_insert,
    execute_query,
    execute_update,
    get_db,
)

# ============================================================
# Blueprint 定义
# ============================================================
players_bp = Blueprint("players", __name__, url_prefix="/players")

# ============================================================
# 常量定义
# ============================================================

# 运动等级选项（与数据库 ENUM 对齐）
SKILL_LEVEL_CHOICES = [
    ("二级运动员", "二级运动员"),
    ("一级运动员", "一级运动员"),
    ("国家级", "国家级"),
    ("健将级", "健将级"),
    ("青年队", "青年队"),
]

# 伤病状态选项（与数据库 ENUM 对齐）
INJURY_STATUS_CHOICES = [
    ("健康", "健康"),
    ("观察中", "观察中"),
    ("康复中", "康复中"),
    ("伤病中", "伤病中"),
]

# 性别选项
GENDER_CHOICES = [("男", "男"), ("女", "女")]


# ============================================================
# 辅助函数
# ============================================================


def calculate_age(birth_date):
    """根据出生日期计算年龄。

    用于列表展示和详情页，将数据库的 birth_date 字段转换为年龄显示。
    如果 birth_date 为 None，返回 "-"。

    Args:
        birth_date: datetime.date 或 str (YYYY-MM-DD) 或 None

    Returns:
        int | str: 年龄数值，无法计算时返回 "-"
    """
    if not birth_date:
        return "-"
    if isinstance(birth_date, str):
        try:
            birth_date = datetime.strptime(birth_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return "-"
    today = datetime.now().date()
    # 考虑月份和日期：如果今年生日还没过，年龄减 1
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def get_injury_status_badge_class(status):
    """根据伤病状态返回 Bootstrap 徽章样式类名。

    用于前端列表和详情页的状态可视化展示。

    Args:
        status: 伤病状态字符串

    Returns:
        str: Bootstrap badge class
    """
    badge_map = {
        "健康": "text-bg-success",
        "观察中": "text-bg-warning",
        "康复中": "text-bg-info",
        "伤病中": "text-bg-danger",
    }
    return badge_map.get(status, "text-bg-secondary")


# ============================================================
# 路由 1: 运动员列表（含多条件动态组合查询）
# ============================================================


@players_bp.route("/", endpoint="list")
@role_required("admin", "coach")
def players_list():
    """运动员档案列表页 + 多条件动态组合查询。

    【核心功能 - 多条件动态组合查询】
    支持以下 8 个维度的交叉筛选：
      1. 学号 (student_no)        - LIKE 模糊匹配
      2. 姓名 (name)              - LIKE 模糊匹配
      3. 性别 (gender)            - ENUM 精确匹配
      4. 运动等级 (skill_level)   - ENUM 精确匹配
      5. 打法 (play_style)        - LIKE 模糊匹配
      6. 握拍方式 (grip)          - LIKE 模糊匹配
      7. 伤病状态 (injury_status) - ENUM 精确匹配
      8. 年龄范围 (age_min/age_max) - 通过 birth_date 计算列筛选

    条件逻辑:
      - AND 模式 (默认): 所有非空条件同时满足
      - OR 模式: 满足任意一个非空条件即可

    【动态 WHERE 子句构建原理】
    使用 build_where_clause() 函数：
      1. 遍历 8 个筛选条件，将非空条件的 SQL 片段加入 conditions 列表
      2. 使用用户选择的 logic (AND/OR) 连接条件
      3. 参数化查询（%s 占位符），防止 SQL 注入
      4. 无条件时返回全部运动员

    URL 参数:
        student_no   - 学号关键词（模糊匹配）
        name         - 姓名关键词（模糊匹配）
        gender       - 性别（精确匹配）
        skill_level  - 运动等级（精确匹配）
        play_style   - 打法关键词（模糊匹配）
        grip         - 握拍方式关键词（模糊匹配）
        injury_status- 伤病状态（精确匹配）
        age_min      - 最小年龄
        age_max      - 最大年龄
        logic        - 条件逻辑：and / or（默认 and）
        page         - 分页页码（默认 1）
    """
    # ---- 获取请求参数 ----
    student_no = request.args.get("student_no", "").strip()
    name = request.args.get("name", "").strip()
    gender = request.args.get("gender", "").strip()
    skill_level = request.args.get("skill_level", "").strip()
    play_style = request.args.get("play_style", "").strip()
    grip = request.args.get("grip", "").strip()
    injury_status = request.args.get("injury_status", "").strip()
    age_min = request.args.get("age_min", "").strip()
    age_max = request.args.get("age_max", "").strip()
    logic = request.args.get("logic", "and").strip().upper()
    if logic not in ("AND", "OR"):
        logic = "AND"

    # ---- 构建动态筛选条件 ----
    # 每个元素为 (SQL 条件片段, 参数值)
    # 文本类字段使用 LIKE 模糊匹配
    # 枚举类字段使用 = 精确匹配
    # 年龄范围使用 birth_date 计算列
    filter_list = [
        # 学号 - 模糊匹配
        ("athlete.student_no LIKE %s", build_like_pattern(student_no)),
        # 姓名 - 模糊匹配
        ("athlete.name LIKE %s", build_like_pattern(name)),
        # 性别 - 精确匹配
        ("athlete.gender = %s", gender if gender else None),
        # 运动等级 - 精确匹配
        ("athlete.skill_level = %s", skill_level if skill_level else None),
        # 打法 - 模糊匹配
        ("athlete.play_style LIKE %s", build_like_pattern(play_style)),
        # 握拍方式 - 模糊匹配
        ("athlete.grip LIKE %s", build_like_pattern(grip)),
        # 伤病状态 - 精确匹配
        ("athlete.injury_status = %s", injury_status if injury_status else None),
        # 最小年龄 - 通过 birth_date 计算
        (
            "YEAR(CURDATE()) - YEAR(athlete.birth_date) >= %s",
            int(age_min) if age_min.isdigit() else None,
        ),
        # 最大年龄 - 通过 birth_date 计算
        (
            "YEAR(CURDATE()) - YEAR(athlete.birth_date) <= %s",
            int(age_max) if age_max.isdigit() else None,
        ),
    ]

    # 调用核心函数构建 WHERE 子句
    where_clause, params = build_where_clause(filter_list, logic=logic)

    # ---- 查询 ----
    # 基础 SELECT（使用 LEFT JOIN 关联教练信息，为后续扩展预留）
    base_sql = """
        SELECT
            athlete.*,
            COALESCE(c.name, '-') AS coach_name
        FROM athlete
        LEFT JOIN (
            SELECT DISTINCT athlete_id, coach_id FROM training_plan
        ) tp ON tp.athlete_id = athlete.id
        LEFT JOIN coach c ON c.id = tp.coach_id
    """

    # 计数查询（用于统计命中数）
    count_sql = f"SELECT COUNT(*) AS total FROM athlete{where_clause}"

    # 数据查询（按创建时间倒序）
    data_sql = f"{base_sql}{where_clause} ORDER BY athlete.id DESC"

    # 执行查询
    players = execute_query(data_sql, tuple(params))
    total_result = execute_query(count_sql, tuple(params))
    total_count = total_result[0]["total"] if total_result else 0

    # 统计激活的筛选条件数（用于前端展示）
    active_condition_count = sum(
        1
        for v in [
            student_no,
            name,
            gender,
            skill_level,
            play_style,
            grip,
            injury_status,
            age_min if age_min.isdigit() else "",
            age_max if age_max.isdigit() else "",
        ]
        if v
    )

    # ---- 计算年龄并附加到每个运动员 ----
    for player in players:
        player["age"] = calculate_age(player.get("birth_date"))

    # ---- 渲染模板 ----
    return render_template(
        "players/list.html",
        players=players,
        total_count=total_count,
        active_condition_count=active_condition_count,
        logic=logic,
        # 将选项传递到模板，便于筛选表单回填
        skill_level_choices=SKILL_LEVEL_CHOICES,
        injury_status_choices=INJURY_STATUS_CHOICES,
    )


# ============================================================
# 路由 2: 新增运动员
# ============================================================


@players_bp.route("/create", methods=["GET", "POST"], endpoint="create")
@role_required("admin")
def players_create():
    """新增运动员档案。

    GET:  渲染空白表单
    POST: 校验表单数据 → 写入数据库 → 重定向到列表页

    校验规则:
      - 学号: 必填，不可与已有运动员重复（UNIQUE 约束）
      - 姓名: 必填，最多 50 字符
      - 性别: 必选，ENUM 值校验
      - 出生日期: 可选，格式 YYYY-MM-DD
      - 运动等级: 必选，ENUM 值校验
      - 联系电话: 可选，最多 20 字符
    """
    if request.method == "GET":
        return render_template(
            "players/create.html",
            skill_level_choices=SKILL_LEVEL_CHOICES,
            gender_choices=GENDER_CHOICES,
        )

    # ---- POST: 处理表单提交 ----
    # 获取表单数据
    student_no = request.form.get("student_no", "").strip()
    name = request.form.get("name", "").strip()
    gender = request.form.get("gender", "").strip()
    birth_date = request.form.get("birth_date", "").strip()
    team = request.form.get("team", "").strip()
    skill_level = request.form.get("skill_level", "").strip()
    play_style = request.form.get("play_style", "").strip()
    grip = request.form.get("grip", "").strip()
    contact_phone = request.form.get("contact_phone", "").strip()

    # ---- 服务端数据校验 ----
    errors = []

    if not student_no:
        errors.append("学号不能为空。")
    elif len(student_no) > 20:
        errors.append("学号不能超过 20 个字符。")

    if not name:
        errors.append("姓名不能为空。")
    elif len(name) > 50:
        errors.append("姓名不能超过 50 个字符。")

    if gender not in ("男", "女"):
        errors.append("请选择有效的性别。")

    if skill_level not in [c[0] for c in SKILL_LEVEL_CHOICES]:
        errors.append("请选择有效的运动等级。")

    # 校验出生日期格式
    if birth_date:
        try:
            datetime.strptime(birth_date, "%Y-%m-%d")
        except ValueError:
            errors.append("出生日期格式不正确，请使用 YYYY-MM-DD 格式。")

    # 校验联系电话
    if contact_phone and len(contact_phone) > 20:
        errors.append("联系电话不能超过 20 个字符。")

    # 校验学号唯一性
    if student_no:
        existing = execute_query(
            "SELECT id FROM athlete WHERE student_no = %s", (student_no,)
        )
        if existing:
            errors.append(f"学号 {student_no} 已存在，请使用不同的学号。")

    if errors:
        for error in errors:
            flash(error, "danger")
        # 保留用户已填写的数据，回填表单
        return render_template(
            "players/create.html",
            skill_level_choices=SKILL_LEVEL_CHOICES,
            gender_choices=GENDER_CHOICES,
            form_data=request.form,
        )

    # ---- 执行插入 ----
    try:
        insert_sql = """
            INSERT INTO athlete
                (student_no, name, gender, birth_date, team, skill_level,
                 play_style, grip, contact_phone, injury_status)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, '健康')
        """
        new_id = execute_insert(
            insert_sql,
            (
                student_no,
                name,
                gender,
                birth_date if birth_date else None,
                team if team else None,
                skill_level,
                play_style if play_style else None,
                grip if grip else None,
                contact_phone if contact_phone else None,
            ),
        )
        flash(f"运动员「{name}」档案创建成功。", "success")
        return redirect(url_for("players.list"))

    except Exception as e:
        flash(f"创建运动员失败：{e}", "danger")
        return render_template(
            "players/create.html",
            skill_level_choices=SKILL_LEVEL_CHOICES,
            gender_choices=GENDER_CHOICES,
            form_data=request.form,
        )


# ============================================================
# 路由 3: 运动员详情
# ============================================================


@players_bp.route("/<int:player_id>", endpoint="detail")
@role_required("admin", "coach")
def players_detail(player_id):
    """运动员综合详情页。

    展示内容:
      - 基本信息（从 athlete 表读取）
      - 训练计划数（从 training_plan 表 COUNT）
      - 技术评估平均分（从 technical_record 表 AVG）
      - 体能测试平均分（从 fitness_report 表 AVG）
      - 伤病记录列表（从 injury_record 表最新 5 条）
      - 近期比赛记录（从 match_record 表最新 5 条）

    说明: 此页面聚合了运动员的综合档案信息，数据来源跨越多张表，
    体现了多表关联查询的设计思想。
    """
    # 查询运动员基本信息
    athlete = execute_query(
        "SELECT * FROM athlete WHERE id = %s", (player_id,), fetch_one=True
    )

    if not athlete:
        flash("未找到该运动员。", "warning")
        return redirect(url_for("players.list"))

    # 计算年龄
    athlete["age"] = calculate_age(athlete.get("birth_date"))

    # 统计训练计划数量与总时长
    training_stats = execute_query(
        """
        SELECT
            COUNT(*) AS total_plans,
            COALESCE(SUM(hours), 0) AS total_hours,
            COUNT(CASE WHEN status = '进行中' THEN 1 END) AS active_plans,
            COUNT(CASE WHEN status = '已完成' THEN 1 END) AS completed_plans
        FROM training_plan
        WHERE athlete_id = %s
        """,
        (player_id,),
        fetch_one=True,
    )

    # 统计技术评估数据
    tech_stats = execute_query(
        """
        SELECT
            COUNT(*) AS total_records,
            ROUND(AVG(forehand_score), 2) AS avg_forehand,
            ROUND(AVG(backhand_score), 2) AS avg_backhand,
            ROUND(AVG(serve_score), 2) AS avg_serve,
            ROUND(AVG(footwork_score), 2) AS avg_footwork,
            ROUND(AVG(reaction_score), 2) AS avg_reaction,
            ROUND(AVG(overall_score), 2) AS avg_overall
        FROM technical_record
        WHERE athlete_id = %s
        """,
        (player_id,),
        fetch_one=True,
    )

    # 统计体能测试数据
    fitness_stats = execute_query(
        """
        SELECT
            COUNT(*) AS total_tests,
            ROUND(AVG(upper_strength), 2) AS avg_upper,
            ROUND(AVG(lower_strength), 2) AS avg_lower,
            ROUND(AVG(flexibility), 2) AS avg_flexibility,
            ROUND(AVG(endurance), 2) AS avg_endurance,
            ROUND(AVG(speed), 2) AS avg_speed,
            ROUND(AVG(overall_score), 2) AS avg_overall
        FROM fitness_report
        WHERE athlete_id = %s
        """,
        (player_id,),
        fetch_one=True,
    )

    # 查询最近 5 条伤病记录
    injury_records = execute_query(
        """
        SELECT * FROM injury_record
        WHERE athlete_id = %s
        ORDER BY injury_date DESC
        LIMIT 5
        """,
        (player_id,),
    )

    # 查询最近 5 条比赛记录
    match_records = execute_query(
        """
        SELECT * FROM match_record
        WHERE athlete_id = %s
        ORDER BY match_date DESC
        LIMIT 5
        """,
        (player_id,),
    )

    # 统计胜负率
    match_stats = execute_query(
        """
        SELECT
            COUNT(*) AS total_matches,
            COUNT(CASE WHEN result = '胜' THEN 1 END) AS wins,
            COUNT(CASE WHEN result = '负' THEN 1 END) AS losses,
            COUNT(CASE WHEN result = '平' THEN 1 END) AS draws
        FROM match_record
        WHERE athlete_id = %s
        """,
        (player_id,),
        fetch_one=True,
    )

    return render_template(
        "players/detail.html",
        athlete=athlete,
        training_stats=training_stats,
        tech_stats=tech_stats,
        fitness_stats=fitness_stats,
        injury_records=injury_records,
        match_records=match_records,
        match_stats=match_stats,
        injury_status_badge_class=get_injury_status_badge_class(
            athlete.get("injury_status", "")
        ),
    )


# ============================================================
# 路由 4: 编辑运动员
# ============================================================


@players_bp.route("/<int:player_id>/edit", methods=["GET", "POST"], endpoint="edit")
@role_required("admin")
def players_edit(player_id):
    """编辑运动员档案信息。

    GET:  读取现有数据并回填到编辑表单
    POST: 校验表单数据 → 更新数据库 → 重定向到详情页

    与新增的区别：
      - 学号唯一性校验时需要排除当前运动员自身
      - 预填表单数据方便用户修改
    """
    # 查询目标运动员
    athlete = execute_query(
        "SELECT * FROM athlete WHERE id = %s", (player_id,), fetch_one=True
    )

    if not athlete:
        flash("未找到该运动员。", "warning")
        return redirect(url_for("players.list"))

    if request.method == "GET":
        return render_template(
            "players/edit.html",
            athlete=athlete,
            skill_level_choices=SKILL_LEVEL_CHOICES,
            gender_choices=GENDER_CHOICES,
            injury_status_choices=INJURY_STATUS_CHOICES,
        )

    # ---- POST: 处理表单提交 ----
    student_no = request.form.get("student_no", "").strip()
    name = request.form.get("name", "").strip()
    gender = request.form.get("gender", "").strip()
    birth_date = request.form.get("birth_date", "").strip()
    team = request.form.get("team", "").strip()
    skill_level = request.form.get("skill_level", "").strip()
    play_style = request.form.get("play_style", "").strip()
    grip = request.form.get("grip", "").strip()
    contact_phone = request.form.get("contact_phone", "").strip()
    # 伤病状态字段主要为触发器预留，管理员可在编辑页手动修正
    injury_status = request.form.get("injury_status", "").strip()

    # ---- 服务端校验 ----
    errors = []

    if not student_no:
        errors.append("学号不能为空。")
    elif len(student_no) > 20:
        errors.append("学号不能超过 20 个字符。")

    if not name:
        errors.append("姓名不能为空。")
    elif len(name) > 50:
        errors.append("姓名不能超过 50 个字符。")

    if gender not in ("男", "女"):
        errors.append("请选择有效的性别。")

    if skill_level not in [c[0] for c in SKILL_LEVEL_CHOICES]:
        errors.append("请选择有效的运动等级。")

    # 伤病状态校验（注意：此字段通常在触发器自动维护，手动修改需谨慎）
    if injury_status and injury_status not in [c[0] for c in INJURY_STATUS_CHOICES]:
        errors.append("请选择有效的伤病状态。")

    if birth_date:
        try:
            datetime.strptime(birth_date, "%Y-%m-%d")
        except ValueError:
            errors.append("出生日期格式不正确。")

    # 学号唯一性校验：排除当前运动员自身
    if student_no and student_no != athlete["student_no"]:
        existing = execute_query(
            "SELECT id FROM athlete WHERE student_no = %s AND id != %s",
            (student_no, player_id),
        )
        if existing:
            errors.append(f"学号 {student_no} 已被其他运动员使用。")

    if errors:
        for error in errors:
            flash(error, "danger")
        return render_template(
            "players/edit.html",
            athlete=athlete,
            skill_level_choices=SKILL_LEVEL_CHOICES,
            gender_choices=GENDER_CHOICES,
            injury_status_choices=INJURY_STATUS_CHOICES,
        )

    # ---- 执行更新 ----
    try:
        update_sql = """
            UPDATE athlete
            SET student_no   = %s,
                name         = %s,
                gender       = %s,
                birth_date   = %s,
                team         = %s,
                skill_level  = %s,
                play_style   = %s,
                grip         = %s,
                contact_phone = %s,
                injury_status = %s,
                update_time  = NOW()
            WHERE id = %s
        """
        affected = execute_update(
            update_sql,
            (
                student_no,
                name,
                gender,
                birth_date if birth_date else None,
                team if team else None,
                skill_level,
                play_style if play_style else None,
                grip if grip else None,
                contact_phone if contact_phone else None,
                injury_status if injury_status else "健康",
                player_id,
            ),
        )
        flash(f"运动员「{name}」档案更新成功。", "success")
        return redirect(url_for("players.detail", player_id=player_id))

    except Exception as e:
        flash(f"更新运动员失败：{e}", "danger")
        return render_template(
            "players/edit.html",
            athlete=athlete,
            skill_level_choices=SKILL_LEVEL_CHOICES,
            gender_choices=GENDER_CHOICES,
            injury_status_choices=INJURY_STATUS_CHOICES,
        )


# ============================================================
# 路由 5: 删除运动员
# ============================================================


@players_bp.route("/<int:player_id>/delete", methods=["POST"], endpoint="delete")
@role_required("admin")
def players_delete(player_id):
    """删除运动员档案。

    数据库层面的处理:
      - athlete 表的外键均设置了 ON DELETE CASCADE
      - 删除运动员时，其关联的训练计划、技术记录、体能报告、
        伤病记录、比赛记录将自动级联删除
      - 教练表不受影响（training_plan → coach 使用 RESTRICT）

    前端确认:
      - 删除操作需要用户在弹窗中确认（见 list.html 中的 Modal）
      - 此处接收 POST 请求执行实际删除
    """
    athlete = execute_query(
        "SELECT name FROM athlete WHERE id = %s", (player_id,), fetch_one=True
    )

    if not athlete:
        flash("未找到该运动员。", "warning")
        return redirect(url_for("players.list"))

    try:
        affected = execute_update(
            "DELETE FROM athlete WHERE id = %s", (player_id,)
        )
        flash(f"运动员「{athlete['name']}」及其关联数据已删除。", "success")
    except Exception as e:
        flash(f"删除失败：{e}", "danger")

    return redirect(url_for("players.list"))


# ============================================================
# 路由 6: 存储过程调用示例（按运动等级筛选）
# ============================================================


@players_bp.route("/filter-by-level", endpoint="filter_by_level")
def players_filter_by_level():
    """调用存储过程 sp_filter_athletes_by_level 筛选运动员。

    这是存储过程调用示例，展示如何从 Flask 调用 MySQL 存储过程。
    实际业务中可复用此模式调用任意存储过程。

    存储过程定义（在 sql/member2_advanced_database.sql 中）:
        CREATE PROCEDURE sp_filter_athletes_by_level(IN p_skill_level VARCHAR(20))
        BEGIN
            SELECT ... FROM athlete
            WHERE p_skill_level IS NULL OR p_skill_level = '' OR skill_level = p_skill_level
            ORDER BY skill_level, name;
        END
    """
    skill_level = request.args.get("level", "").strip()
    try:
        # 使用 CALL 语句调用存储过程
        players = execute_query(
            "CALL sp_filter_athletes_by_level(%s)", (skill_level if skill_level else "",)
        )
        # 计算年龄
        for player in players:
            player["age"] = calculate_age(player.get("birth_date"))
    except Exception as e:
        flash(f"存储过程调用失败：{e}", "danger")
        return redirect(url_for("players.list"))

    return render_template(
        "players/list.html",
        players=players,
        total_count=len(players),
        active_condition_count=1 if skill_level else 0,
        logic="AND",
        skill_level_choices=SKILL_LEVEL_CHOICES,
        injury_status_choices=INJURY_STATUS_CHOICES,
    )
