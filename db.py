# ============================================================
# 乒乓球运动员综合训练监控管理系统 · 数据库连接模块
# 模块职责: 提供 MySQL 数据库连接管理、上下文管理器与通用查询辅助函数
# 使用技术: PyMySQL + python-dotenv
# 兼容版本: MySQL 5.5+ / MySQL 8.0+
# ============================================================

import os
from contextlib import contextmanager

import pymysql
from dotenv import load_dotenv

# 加载 .env 文件中的数据库配置
load_dotenv()

# ============================================================
# 数据库连接配置
# 优先从环境变量读取，不存在则使用默认值（开发环境）
# ============================================================
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "123"),
    "database": os.getenv("DB_NAME", "pingpang_db"),
    "charset": "utf8",
    # 游标返回字典而非元组，方便按字段名取值
    "cursorclass": pymysql.cursors.DictCursor,
    # 自动提交由各业务模块自行控制（事务场景需要手动 COMMIT）
    "autocommit": False,
}


def get_connection():
    """获取一个新的数据库连接。

    调用方负责在使用完毕后调用 conn.close() 归还连接。
    生产环境建议替换为连接池（如 DBUtils.PooledDB 或 SQLAlchemy 连接池）。

    Returns:
        pymysql.Connection: 配置好的数据库连接对象
    """
    return pymysql.connect(**DB_CONFIG)


@contextmanager
def get_db():
    """数据库连接上下文管理器。

    用法:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM athlete")
            rows = cursor.fetchall()

    无论是否发生异常，退出 with 块时连接自动关闭。
    需要在 with 块内手动调用 conn.commit() 提交事务。
    """
    conn = pymysql.connect(**DB_CONFIG)
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def get_cursor(conn=None):
    """获取游标的上下文管理器，自动关闭游标。

    用法:
        with get_db() as conn:
            with get_cursor(conn) as cursor:
                cursor.execute("SELECT * FROM athlete")
                rows = cursor.fetchall()

    如果 conn 为 None，会创建新的连接并在退出时关闭。
    """
    own_conn = conn is None
    if own_conn:
        conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    try:
        yield cursor
    finally:
        cursor.close()
        if own_conn:
            conn.close()


def execute_query(sql, params=None, fetch_one=False):
    """执行查询并返回结果集（SELECT 语句）。

    Args:
        sql: SQL 查询语句（使用 %s 占位符）
        params: 查询参数元组或列表
        fetch_one: True 返回单行字典，False 返回列表

    Returns:
        dict | list[dict] | None: 查询结果
    """
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute(sql, params)
            if fetch_one:
                return cursor.fetchone()
            return cursor.fetchall()


def execute_update(sql, params=None):
    """执行增删改操作并提交事务（INSERT/UPDATE/DELETE 语句）。

    Args:
        sql: SQL 语句（使用 %s 占位符）
        params: 参数元组或列表

    Returns:
        int: 受影响的行数（rowcount）
    """
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            affected = cursor.execute(sql, params)
            conn.commit()
            return affected


def execute_insert(sql, params=None):
    """执行插入操作并返回自增主键 ID。

    Args:
        sql: INSERT 语句（使用 %s 占位符）
        params: 参数元组或列表

    Returns:
        int: 新插入行的自增 ID
    """
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute(sql, params)
            conn.commit()
            return cursor.lastrowid


def execute_transaction(operations):
    """在单个事务中执行多条 SQL 操作。

    所有操作要么全部成功提交，要么全部回滚。
    适用于"训练数据 + 体能数据同步提交"等需要原子性的场景。

    Args:
        operations: 可调用对象列表，每个接收 cursor 参数并执行 SQL

    Raises:
        Exception: 任意操作失败时回滚所有已执行的变更

    用法:
        def op1(cursor):
            cursor.execute("INSERT INTO training_plan (...) VALUES (...)")
        def op2(cursor):
            cursor.execute("INSERT INTO fitness_report (...) VALUES (...)")
        execute_transaction([op1, op2])
    """
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            try:
                for op in operations:
                    op(cursor)
                conn.commit()
            except Exception:
                conn.rollback()
                raise


# ============================================================
# 运动员模块专用 SQL 构建工具
# ============================================================

def build_where_clause(filters, logic="AND"):
    """动态构建 SQL WHERE 子句。

    这是运动员模块"多条件动态组合查询"的核心函数。
    根据用户输入的非空筛选条件，动态拼接 WHERE 子句和参数列表。

    设计原理:
        1. 遍历 filters 列表中的每个筛选条件
        2. 如果条件值非空，将其 SQL 片段和参数加入结果
        3. 使用 logic 参数控制条件间的连接词（AND / OR）
        4. 返回 (where_clause, params) 元组，可直接拼接到 SELECT 语句

    Args:
        filters: 筛选条件列表，每个元素为 (condition_sql, param_value) 元组
                 condition_sql 示例: "name LIKE %s"
                 如果 param_value 为空字符串或 None，该条件将被跳过
        logic: 条件连接逻辑，"AND" 或 "OR"

    Returns:
        tuple: (where_clause_str, params_list)
               - where_clause_str: " WHERE cond1 AND cond2 ..." 或 "" (无条件时)
               - params_list: 对应的参数值列表

    用法:
        filters = [
            ("name LIKE %s", request.args.get("name")),
            ("gender = %s", request.args.get("gender")),
        ]
        where_clause, params = build_where_clause(filters, logic="AND")
        sql = f"SELECT * FROM athlete {where_clause}"
        rows = execute_query(sql, params)
    """
    conditions = []
    params = []

    for condition_sql, param_value in filters:
        # 跳过空值条件（None、空字符串、仅空白字符）
        if param_value is None or (isinstance(param_value, str) and param_value.strip() == ""):
            continue
        conditions.append(condition_sql)
        params.append(param_value)

    if not conditions:
        return "", []

    separator = f" {logic} "
    where_clause = " WHERE " + separator.join(conditions)
    return where_clause, params


def build_like_pattern(keyword):
    """构建 SQL LIKE 模糊匹配模式。

    将用户输入的关键词包装为 %keyword% 格式，
    同时对 SQL 特殊字符（%、_）进行转义以防止意外通配。

    Args:
        keyword: 用户输入的搜索关键词

    Returns:
        str: 转义后的模糊匹配模式，如 "%王%"
    """
    if not keyword:
        return None
    # 转义 LIKE 通配符：\% 和 \_
    escaped = keyword.replace("%", r"\%").replace("_", r"\_")
    return f"%{escaped}%"


def paginate_query(base_sql, count_sql, params, page=1, per_page=10):
    """对 SQL 查询结果进行分页。

    Args:
        base_sql: 数据查询 SQL（不含 LIMIT）
        count_sql: 计数查询 SQL
        params: 查询参数列表
        page: 当前页码（从 1 开始）
        per_page: 每页记录数

    Returns:
        dict: {
            "items": 当前页数据列表,
            "total": 总记录数,
            "page": 当前页码,
            "per_page": 每页条数,
            "pages": 总页数
        }
    """
    offset = (page - 1) * per_page
    paginated_sql = f"{base_sql} LIMIT {per_page} OFFSET {offset}"

    items = execute_query(paginated_sql, params)
    total_result = execute_query(count_sql, params)
    total = total_result[0]["total"] if total_result else 0
    pages = (total + per_page - 1) // per_page if total > 0 else 0

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
    }
