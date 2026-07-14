from datetime import date, datetime
from decimal import Decimal
import os

from pymysql import MySQLError

from repositories.db_helpers import (
    DATABASE_SETUP_ERROR_CODES,
    execute_affected,
    execute_many,
    execute_write,
    fetch_all,
    fetch_one,
    is_database_setup_error,
)


SERVE_FREQUENCY_OPTIONS = ["高", "中", "低"]
LANDING_CONCENTRATION_OPTIONS = ["集中", "较为集中", "一般", "较为分散", "分散"]
# 兼容旧引用
LANDING_DISTRIBUTION_OPTIONS = LANDING_CONCENTRATION_OPTIONS

_DEMO_FOOTWORK_SPECS = [
    {"athlete_id": 1, "training_date": "2026-07-03", "footwork_code": "parallel_step", "duration_minutes": 38, "set_count": 6, "note": "并步衔接质量稳定，需继续加强还原速度。", "created_by": "coach"},
    {"athlete_id": 2, "training_date": "2026-07-04", "footwork_code": "single_step", "duration_minutes": 32, "set_count": 5, "note": "单步启动偏慢，注意降低腕部负荷。", "created_by": "coach"},
    {"athlete_id": 4, "training_date": "2026-07-08", "footwork_code": "composite_step", "duration_minutes": 25, "set_count": 4, "note": "康复期以小范围综合步法为主。", "created_by": "coach"},
]

_DEMO_TECHNIQUE_SPECS = [
    {"athlete_id": 1, "training_date": "2026-07-10", "technique_code": "serve_attack", "multi_ball_count": 420, "serve_frequency": "高", "plan_execution_rate": 88.0, "on_table_rate": 86.0, "landing_items": [{"landing_code": "near_left", "concentration": "较为集中"}, {"landing_code": "mid_table", "concentration": "集中"}], "qualitative_comment": "发球抢攻执行到位，后半程稳定性略降。", "created_by": "admin"},
    {"athlete_id": 3, "training_date": "2026-07-06", "technique_code": "forehand_smash", "multi_ball_count": 380, "serve_frequency": "中", "plan_execution_rate": 82.0, "on_table_rate": 88.0, "landing_items": [{"landing_code": "wide_right", "concentration": "集中"}], "qualitative_comment": "侧身后扣杀得分率高，回位速度仍需加强。", "created_by": "coach"},
    {"athlete_id": 3, "training_date": "2026-07-12", "technique_code": "backhand_flick", "multi_ball_count": 360, "serve_frequency": "中", "plan_execution_rate": 79.0, "on_table_rate": 83.0, "landing_items": [{"landing_code": "body_line", "concentration": "一般"}], "qualitative_comment": "反手拧拉线路清晰，连续变线后重心保持较好。", "created_by": "coach"},
]

_ADDITIONAL_FOOTWORK_CODES = ["single_step", "parallel_step", "cross_step", "composite_step", "shuffle_step", "stride_step", "side_step", "recovery_step"]
_ADDITIONAL_TECHNIQUE_CODES = ["forehand_loop", "backhand_flick", "serve_attack", "receive_push_short", "change_direction", "defense_to_attack", "wide_angle", "block"]
_ADDITIONAL_TREND_MONTHS = ["2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07"]

_db_ready = None
SYS_DICTIONARY = []
MEMORY_FOOTWORK_RECORDS = []
MEMORY_TECHNIQUE_TACTIC_RECORDS = []


def build_sys_dictionary():
    items = []
    next_id = 1

    def add(category_type, parent_id, dict_code, dict_name, sort_order=0):
        nonlocal next_id
        item = {
            "id": next_id,
            "category_type": category_type,
            "parent_id": parent_id,
            "dict_code": dict_code,
            "dict_name": dict_name,
            "sort_order": sort_order,
            "is_enabled": True,
        }
        items.append(item)
        next_id += 1
        return item["id"]

    footwork_root = add("footwork", 0, "footwork_root", "步法", 0)
    for code, name, order in [
        ("single_step", "单步", 10),
        ("parallel_step", "并步", 20),
        ("stride_step", "跨步", 30),
        ("cross_step", "交叉步", 40),
        ("shuffle_step", "碎步", 50),
        ("side_step", "侧身步", 60),
        ("composite_step", "综合步法", 70),
        ("recovery_step", "还原步", 80),
    ]:
        add("footwork", footwork_root, code, name, order)

    technique_parents = {}
    for code, name, order in [
        ("serve", "发球", 100),
        ("receive", "接发球", 200),
        ("attack_technique", "进攻技术", 300),
        ("defense_transition", "防守/过渡", 400),
        ("first_three_tactic", "前三板战术", 500),
        ("rally_tactic", "相持战术", 600),
        ("placement_tactic", "落点战术", 700),
        ("attack_defense_switch", "攻防转换", 800),
    ]:
        technique_parents[code] = add("technique_tactic", 0, code, name, order)

    technique_children = {
        "serve": [("serve_underspin", "发下旋球", 10), ("serve_topspin", "发上旋球", 20), ("serve_sidespin", "发侧旋球", 30), ("serve_long", "发长球", 40), ("serve_short", "发短球", 50)],
        "receive": [("receive_flick", "挑打", 10), ("receive_push_short", "摆短", 20), ("receive_loop", "接发抢拉", 30), ("receive_control", "控接", 40)],
        "attack_technique": [("forehand_loop", "正手前冲弧圈球", 10), ("backhand_flick", "反手拧拉", 20), ("forehand_smash", "正手扣杀", 30), ("backhand_loop", "反手弧圈", 40)],
        "defense_transition": [("block", "挡球", 10), ("chop", "削球", 20), ("lob", "放高球", 30), ("counter_loop", "对拉过渡", 40)],
        "first_three_tactic": [("serve_attack", "发球抢攻", 10), ("receive_attack", "接发抢攻", 20), ("third_ball_attack", "第三板进攻", 30)],
        "rally_tactic": [("change_pace", "变节奏", 10), ("change_spin", "变旋转", 20), ("change_direction", "变线路", 30)],
        "placement_tactic": [("wide_angle", "大角度调动", 10), ("body_attack", "追身球", 20), ("deep_short", "深浅结合", 30)],
        "attack_defense_switch": [("defense_to_attack", "防转攻", 10), ("attack_to_defense", "攻转防", 20)],
    }
    for parent_code, children in technique_children.items():
        parent_id = technique_parents[parent_code]
        for code, name, order in children:
            add("technique_tactic", parent_id, code, name, order)

    landing_root = add("landing_point", 0, "landing_root", "落点区域", 0)
    for code, name, order in [
        ("near_left", "近台左侧", 10),
        ("near_right", "近台右侧", 20),
        ("mid_table", "中台", 30),
        ("far_table", "远台", 40),
        ("body_line", "追身位", 50),
        ("wide_left", "大角度左", 60),
        ("wide_right", "大角度右", 70),
    ]:
        add("landing_point", landing_root, code, name, order)

    return items


def normalize_date_value(value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]


def normalize_decimal(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value


def find_dict_by_id(dict_id):
    return next((item for item in SYS_DICTIONARY if item["id"] == dict_id), None)


def find_dict_by_code(dict_code):
    return next((item for item in SYS_DICTIONARY if item["dict_code"] == dict_code), None)


def get_dict_children(category_type, parent_id=0, leaf_only=False):
    children = [
        item
        for item in SYS_DICTIONARY
        if item["category_type"] == category_type and item["parent_id"] == parent_id and item["is_enabled"]
    ]
    children.sort(key=lambda item: item["sort_order"])
    if leaf_only:
        return [item for item in children if not any(child["parent_id"] == item["id"] for child in SYS_DICTIONARY)]
    return children


def get_footwork_options():
    root = find_dict_by_code("footwork_root")
    return get_dict_children("footwork", root["id"] if root else 0)


def get_technique_categories():
    return get_dict_children("technique_tactic", 0)


def get_technique_options():
    options = []
    for category in get_technique_categories():
        options.extend(get_dict_children("technique_tactic", category["id"]))
    return options


def get_landing_options():
    root = find_dict_by_code("landing_root")
    return get_dict_children("landing_point", root["id"] if root else 0)


def normalize_landing_concentration(value):
    text = str(value or "").strip()
    if text in LANDING_CONCENTRATION_OPTIONS:
        return text
    return ""


def materialize_landing_items(spec):
    items = []
    for entry in spec.get("landing_items", []):
        landing = None
        if entry.get("landing_code"):
            landing = find_dict_by_code(entry["landing_code"])
        elif entry.get("landing_dict_id"):
            landing = find_dict_by_id(entry["landing_dict_id"])
        concentration = normalize_landing_concentration(entry.get("concentration", ""))
        if landing and concentration:
            items.append({"landing_dict_id": landing["id"], "concentration": concentration})
    return items


def format_landing_distribution_items(items):
    labels = []
    for item in items or []:
        landing = find_dict_by_id(item.get("landing_dict_id"))
        concentration = normalize_landing_concentration(item.get("concentration", ""))
        if landing and concentration:
            labels.append(f"{landing['dict_name']}（{concentration}）")
    return "、".join(labels)


def resolve_dict_by_name(name, category_type, parent_id=None):
    text = str(name or "").strip()
    if not text:
        return None
    for item in SYS_DICTIONARY:
        if item["category_type"] != category_type or not item["is_enabled"]:
            continue
        if parent_id is not None and item["parent_id"] != parent_id:
            continue
        if item["dict_name"] == text or item["dict_code"] == text:
            return item
    return None


def using_database():
    return _db_ready is True


def _check_database_ready():
    global _db_ready
    if os.getenv("TRAINING_STORAGE", "").strip().lower() == "memory":
        _db_ready = False
        return False
    if _db_ready is not None:
        return _db_ready
    try:
        fetch_one(
            """
            SELECT 1
            FROM footwork_training ft
            JOIN technique_tactic_training tt ON 1 = 1
            JOIN sys_dictionary sd ON 1 = 1
            LIMIT 1
            """
        )
        _db_ready = True
    except MySQLError as exc:
        if is_database_setup_error(exc):
            _db_ready = False
        else:
            raise
    except Exception:
        _db_ready = False
    return _db_ready


def _load_sys_dictionary_from_db():
    rows = fetch_all(
        """
        SELECT id, category_type, parent_id, dict_code, dict_name, sort_order, is_enabled
        FROM sys_dictionary
        WHERE is_enabled = 1
        ORDER BY sort_order, id
        """
    )
    return [
        {
            "id": row["id"],
            "category_type": row["category_type"],
            "parent_id": row["parent_id"],
            "dict_code": row["dict_code"],
            "dict_name": row["dict_name"],
            "sort_order": row["sort_order"],
            "is_enabled": bool(row["is_enabled"]),
        }
        for row in rows
    ]


def reload_sys_dictionary():
    global SYS_DICTIONARY
    if _check_database_ready():
        rows = _load_sys_dictionary_from_db()
        if rows:
            SYS_DICTIONARY = rows
            return SYS_DICTIONARY
    SYS_DICTIONARY = build_sys_dictionary()
    return SYS_DICTIONARY


def _next_memory_id(records):
    return max((item["id"] for item in records), default=0) + 1


def materialize_footwork_spec(spec, record_id=None):
    footwork = find_dict_by_code(spec["footwork_code"])
    return {
        "id": record_id or spec.get("id"),
        "athlete_id": spec["athlete_id"],
        "athlete_name": spec.get("athlete_name", ""),
        "training_date": spec["training_date"],
        "footwork_dict_id": footwork["id"] if footwork else get_footwork_options()[0]["id"],
        "duration_minutes": spec["duration_minutes"],
        "set_count": spec["set_count"],
        "note": spec.get("note", ""),
        "created_by": spec.get("created_by", "coach"),
    }


def materialize_technique_spec(spec, record_id=None):
    technique = find_dict_by_code(spec["technique_code"])
    return {
        "id": record_id or spec.get("id"),
        "athlete_id": spec["athlete_id"],
        "athlete_name": spec.get("athlete_name", ""),
        "training_date": spec["training_date"],
        "technique_dict_id": technique["id"] if technique else get_technique_options()[0]["id"],
        "multi_ball_count": spec["multi_ball_count"],
        "serve_frequency": spec["serve_frequency"],
        "plan_execution_rate": spec["plan_execution_rate"],
        "on_table_rate": spec.get("on_table_rate"),
        "landing_distribution_items": materialize_landing_items(spec),
        "qualitative_comment": spec.get("qualitative_comment", ""),
        "created_by": spec.get("created_by", "coach"),
    }


def _build_additional_demo_records(player_count=22):
    footwork_records = []
    technique_records = []
    for index in range(player_count):
        athlete_id = index + 9
        training_date = f"{_ADDITIONAL_TREND_MONTHS[index % len(_ADDITIONAL_TREND_MONTHS)]}-{(index % 20) + 1:02d}"
        if index % 2 == 0:
            footwork_records.append(
                materialize_footwork_spec(
                    {
                        "athlete_id": athlete_id,
                        "training_date": training_date,
                        "footwork_code": _ADDITIONAL_FOOTWORK_CODES[index % len(_ADDITIONAL_FOOTWORK_CODES)],
                        "duration_minutes": 28 + (index % 7) * 4,
                        "set_count": 4 + (index % 5),
                        "note": f"运动员{athlete_id}完成步法训练，重点跟踪移动衔接和还原质量。",
                        "created_by": "coach" if index % 3 else "admin",
                    },
                    record_id=len(footwork_records) + len(_DEMO_FOOTWORK_SPECS) + 1,
                )
            )
        else:
            technique_records.append(
                materialize_technique_spec(
                    {
                        "athlete_id": athlete_id,
                        "training_date": training_date,
                        "technique_code": _ADDITIONAL_TECHNIQUE_CODES[index % len(_ADDITIONAL_TECHNIQUE_CODES)],
                        "multi_ball_count": 300 + (index % 8) * 25,
                        "serve_frequency": SERVE_FREQUENCY_OPTIONS[index % len(SERVE_FREQUENCY_OPTIONS)],
                        "plan_execution_rate": 70 + (index % 10) * 2,
                        "on_table_rate": 68 + (index % 12) * 2,
                        "landing_items": [
                            {
                                "landing_code": ["near_left", "mid_table", "wide_right", "body_line"][index % 4],
                                "concentration": LANDING_CONCENTRATION_OPTIONS[index % len(LANDING_CONCENTRATION_OPTIONS)],
                            }
                        ],
                        "qualitative_comment": f"运动员{athlete_id}技战术执行稳定，落点变化仍需加强。",
                        "created_by": "coach" if index % 3 else "admin",
                    },
                    record_id=len(technique_records) + len(_DEMO_TECHNIQUE_SPECS) + 1,
                )
            )
    return footwork_records, technique_records


def _seed_memory_records():
    global MEMORY_FOOTWORK_RECORDS, MEMORY_TECHNIQUE_TACTIC_RECORDS
    demo_footwork = [
        materialize_footwork_spec(spec, record_id=index + 1)
        for index, spec in enumerate(_DEMO_FOOTWORK_SPECS)
    ]
    demo_technique = [
        materialize_technique_spec(spec, record_id=index + 1)
        for index, spec in enumerate(_DEMO_TECHNIQUE_SPECS)
    ]
    additional_footwork, additional_technique = _build_additional_demo_records()
    MEMORY_FOOTWORK_RECORDS = demo_footwork + additional_footwork
    MEMORY_TECHNIQUE_TACTIC_RECORDS = demo_technique + additional_technique


def _resolve_created_by_id(operator):
    if not operator:
        return None
    from auth_utils import USERS

    user = USERS.get(operator)
    if user and user.get("coach_id"):
        return int(user["coach_id"])
    return None


def _row_to_footwork(row):
    return {
        "id": row["id"],
        "athlete_id": row["athlete_id"],
        "athlete_name": row.get("athlete_name", ""),
        "training_date": normalize_date_value(row["training_date"]),
        "footwork_dict_id": row["footwork_dict_id"],
        "duration_minutes": int(row["duration_minutes"]),
        "set_count": int(row["set_count"]),
        "note": row.get("note") or "",
        "created_by": row.get("created_by_name") or row.get("created_by") or "",
    }


def _normalize_landing_items(raw_items):
    if not raw_items:
        return []
    if isinstance(raw_items[0], dict):
        return [
            {
                "landing_dict_id": item["landing_dict_id"],
                "concentration": normalize_landing_concentration(item.get("concentration", "")),
            }
            for item in raw_items
            if item.get("landing_dict_id") and normalize_landing_concentration(item.get("concentration", ""))
        ]
    return [{"landing_dict_id": landing_id, "concentration": ""} for landing_id in raw_items]


def _row_to_technique(row, landing_items=None):
    items = _normalize_landing_items(landing_items)
    display = format_landing_distribution_items(items) or str(row.get("landing_distribution") or "").strip()
    return {
        "id": row["id"],
        "athlete_id": row["athlete_id"],
        "athlete_name": row.get("athlete_name", ""),
        "training_date": normalize_date_value(row["training_date"]),
        "technique_dict_id": row["technique_dict_id"],
        "multi_ball_count": int(row["multi_ball_count"]),
        "serve_frequency": row["serve_frequency"],
        "plan_execution_rate": normalize_decimal(row["plan_execution_rate"]) or 0,
        "on_table_rate": normalize_decimal(row.get("on_table_rate")),
        "landing_distribution_items": items,
        "landing_distribution": display,
        "qualitative_comment": row.get("qualitative_comment") or "",
        "created_by": row.get("created_by_name") or row.get("created_by") or "",
    }


def _fetch_landing_items(record_ids):
    if not record_ids:
        return {}
    placeholders = ", ".join(["%s"] * len(record_ids))
    try:
        rows = fetch_all(
            f"""
            SELECT technique_tactic_id, landing_dict_id, concentration_level
            FROM technique_tactic_landing
            WHERE technique_tactic_id IN ({placeholders})
            ORDER BY technique_tactic_id, landing_dict_id
            """,
            tuple(record_ids),
        )
    except MySQLError:
        rows = fetch_all(
            f"""
            SELECT technique_tactic_id, landing_dict_id
            FROM technique_tactic_landing
            WHERE technique_tactic_id IN ({placeholders})
            ORDER BY technique_tactic_id, landing_dict_id
            """,
            tuple(record_ids),
        )
    landing_map = {}
    for row in rows:
        landing_map.setdefault(row["technique_tactic_id"], []).append(
            {
                "landing_dict_id": row["landing_dict_id"],
                "concentration": normalize_landing_concentration(row.get("concentration_level", "")),
            }
        )
    return landing_map


def _clear_landing_records(record_id):
    if using_database():
        execute_write("DELETE FROM technique_tactic_landing WHERE technique_tactic_id = %s", (record_id,))


def _replace_landing_items(record_id, items):
    _clear_landing_records(record_id)
    if not items:
        return
    try:
        execute_many(
            "INSERT INTO technique_tactic_landing (technique_tactic_id, landing_dict_id, concentration_level) VALUES (%s, %s, %s)",
            [(record_id, item["landing_dict_id"], item["concentration"]) for item in items],
        )
    except MySQLError:
        execute_many(
            "INSERT INTO technique_tactic_landing (technique_tactic_id, landing_dict_id) VALUES (%s, %s)",
            [(record_id, item["landing_dict_id"]) for item in items],
        )


def _seed_database_if_empty():
    footwork_count = fetch_one("SELECT COUNT(*) AS total FROM footwork_training")["total"]
    technique_count = fetch_one("SELECT COUNT(*) AS total FROM technique_tactic_training")["total"]
    if footwork_count or technique_count:
        return

    available_athlete_ids = {int(row["id"]) for row in fetch_all("SELECT id FROM athlete")}

    for spec in _DEMO_FOOTWORK_SPECS:
        if spec["athlete_id"] in available_athlete_ids:
            create_footwork_record(materialize_footwork_spec(spec), operator=spec.get("created_by"))
    for spec in _DEMO_TECHNIQUE_SPECS:
        if spec["athlete_id"] in available_athlete_ids:
            create_technique_tactic_record(materialize_technique_spec(spec), operator=spec.get("created_by"))

    for index in range(22):
        athlete_id = index + 9
        if athlete_id not in available_athlete_ids:
            continue
        training_date = f"{_ADDITIONAL_TREND_MONTHS[index % len(_ADDITIONAL_TREND_MONTHS)]}-{(index % 20) + 1:02d}"
        if index % 2 == 0:
            create_footwork_record(
                materialize_footwork_spec(
                    {
                        "athlete_id": athlete_id,
                        "training_date": training_date,
                        "footwork_code": _ADDITIONAL_FOOTWORK_CODES[index % len(_ADDITIONAL_FOOTWORK_CODES)],
                        "duration_minutes": 28 + (index % 7) * 4,
                        "set_count": 4 + (index % 5),
                        "note": f"运动员{athlete_id}完成步法训练。",
                        "created_by": "coach",
                    }
                ),
                operator="coach",
            )
        else:
            create_technique_tactic_record(
                materialize_technique_spec(
                    {
                        "athlete_id": athlete_id,
                        "training_date": training_date,
                        "technique_code": _ADDITIONAL_TECHNIQUE_CODES[index % len(_ADDITIONAL_TECHNIQUE_CODES)],
                        "multi_ball_count": 300 + (index % 8) * 25,
                        "serve_frequency": SERVE_FREQUENCY_OPTIONS[index % len(SERVE_FREQUENCY_OPTIONS)],
                        "plan_execution_rate": 70 + (index % 10) * 2,
                        "on_table_rate": 68 + (index % 12) * 2,
                        "landing_items": [
                            {
                                "landing_code": ["near_left", "mid_table", "wide_right", "body_line"][index % 4],
                                "concentration": LANDING_CONCENTRATION_OPTIONS[index % len(LANDING_CONCENTRATION_OPTIONS)],
                            }
                        ],
                        "qualitative_comment": f"运动员{athlete_id}技战术执行稳定。",
                        "created_by": "coach",
                    }
                ),
                operator="coach",
            )


def initialize_training_storage():
    reload_sys_dictionary()
    if _check_database_ready():
        _seed_database_if_empty()
        return
    _seed_memory_records()


def list_footwork_records(filters=None):
    if using_database():
        return _list_footwork_records_db(filters or {})
    return _list_footwork_records_memory(filters or {})


def list_technique_tactic_records(filters=None):
    if using_database():
        return _list_technique_tactic_records_db(filters or {})
    return _list_technique_tactic_records_memory(filters or {})


def count_footwork_records():
    if using_database():
        return fetch_one("SELECT COUNT(*) AS total FROM footwork_training")["total"]
    return len(MEMORY_FOOTWORK_RECORDS)


def count_technique_tactic_records():
    if using_database():
        return fetch_one("SELECT COUNT(*) AS total FROM technique_tactic_training")["total"]
    return len(MEMORY_TECHNIQUE_TACTIC_RECORDS)


def get_footwork_record(record_id):
    if using_database():
        row = fetch_one(
            """
            SELECT ft.*, a.name AS athlete_name
            FROM footwork_training ft
            JOIN athlete a ON ft.athlete_id = a.id
            WHERE ft.id = %s
            """,
            (record_id,),
        )
        return _row_to_footwork(row) if row else None
    return next((item for item in MEMORY_FOOTWORK_RECORDS if item["id"] == record_id), None)


def get_technique_tactic_record(record_id):
    if using_database():
        row = fetch_one(
            """
            SELECT tt.*, a.name AS athlete_name
            FROM technique_tactic_training tt
            JOIN athlete a ON tt.athlete_id = a.id
            WHERE tt.id = %s
            """,
            (record_id,),
        )
        if not row:
            return None
        landing_map = _fetch_landing_items([record_id])
        return _row_to_technique(row, landing_map.get(record_id, []))
    return next((item for item in MEMORY_TECHNIQUE_TACTIC_RECORDS if item["id"] == record_id), None)


def create_footwork_record(data, operator=None):
    if using_database():
        created_by = _resolve_created_by_id(operator)
        record_id = execute_write(
            """
            INSERT INTO footwork_training
                (athlete_id, training_date, footwork_dict_id, duration_minutes, set_count, note, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                data["athlete_id"],
                data["training_date"],
                data["footwork_dict_id"],
                data["duration_minutes"],
                data["set_count"],
                data.get("note", ""),
                created_by,
            ),
        )
        return record_id

    record = {**data, "id": _next_memory_id(MEMORY_FOOTWORK_RECORDS), "created_by": operator or data.get("created_by", "")}
    MEMORY_FOOTWORK_RECORDS.append(record)
    return record["id"]


def update_footwork_record(record_id, data, operator=None):
    if using_database():
        created_by = _resolve_created_by_id(operator)
        affected = execute_affected(
            """
            UPDATE footwork_training
            SET athlete_id=%s, training_date=%s, footwork_dict_id=%s,
                duration_minutes=%s, set_count=%s, note=%s, created_by=%s
            WHERE id=%s
            """,
            (
                data["athlete_id"],
                data["training_date"],
                data["footwork_dict_id"],
                data["duration_minutes"],
                data["set_count"],
                data.get("note", ""),
                created_by,
                record_id,
            ),
        )
        return affected > 0

    target = next((item for item in MEMORY_FOOTWORK_RECORDS if item["id"] == record_id), None)
    if not target:
        return False
    target.update(data)
    target["created_by"] = operator or target.get("created_by", "")
    return True


def delete_footwork_record(record_id):
    if using_database():
        affected = execute_affected("DELETE FROM footwork_training WHERE id = %s", (record_id,))
        return affected > 0
    target = next((item for item in MEMORY_FOOTWORK_RECORDS if item["id"] == record_id), None)
    if not target:
        return False
    MEMORY_FOOTWORK_RECORDS.remove(target)
    return True


def create_technique_tactic_record(data, operator=None):
    landing_items = data.get("landing_distribution_items", [])
    landing_summary = format_landing_distribution_items(landing_items)
    if using_database():
        created_by = _resolve_created_by_id(operator)
        record_id = execute_write(
            """
            INSERT INTO technique_tactic_training
                (athlete_id, training_date, technique_dict_id, multi_ball_count, serve_frequency,
                 plan_execution_rate, on_table_rate, landing_distribution, qualitative_comment, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                data["athlete_id"],
                data["training_date"],
                data["technique_dict_id"],
                data["multi_ball_count"],
                data["serve_frequency"],
                data["plan_execution_rate"],
                data.get("on_table_rate"),
                landing_summary,
                data.get("qualitative_comment", ""),
                created_by,
            ),
        )
        _replace_landing_items(record_id, landing_items)
        return record_id

    record = {
        **data,
        "id": _next_memory_id(MEMORY_TECHNIQUE_TACTIC_RECORDS),
        "landing_distribution": landing_summary,
        "created_by": operator or data.get("created_by", ""),
    }
    MEMORY_TECHNIQUE_TACTIC_RECORDS.append(record)
    return record["id"]


def update_technique_tactic_record(record_id, data, operator=None):
    landing_items = data.get("landing_distribution_items", [])
    landing_summary = format_landing_distribution_items(landing_items)
    if using_database():
        created_by = _resolve_created_by_id(operator)
        affected = execute_affected(
            """
            UPDATE technique_tactic_training
            SET athlete_id=%s, training_date=%s, technique_dict_id=%s, multi_ball_count=%s,
                serve_frequency=%s, plan_execution_rate=%s, on_table_rate=%s,
                landing_distribution=%s, qualitative_comment=%s, created_by=%s
            WHERE id=%s
            """,
            (
                data["athlete_id"],
                data["training_date"],
                data["technique_dict_id"],
                data["multi_ball_count"],
                data["serve_frequency"],
                data["plan_execution_rate"],
                data.get("on_table_rate"),
                landing_summary,
                data.get("qualitative_comment", ""),
                created_by,
                record_id,
            ),
        )
        if affected <= 0:
            return False
        _replace_landing_items(record_id, landing_items)
        return True

    target = next((item for item in MEMORY_TECHNIQUE_TACTIC_RECORDS if item["id"] == record_id), None)
    if not target:
        return False
    target.update(data)
    target["landing_distribution"] = landing_summary
    target["created_by"] = operator or target.get("created_by", "")
    return True


def delete_technique_tactic_record(record_id):
    if using_database():
        affected = execute_affected("DELETE FROM technique_tactic_training WHERE id = %s", (record_id,))
        return affected > 0
    target = next((item for item in MEMORY_TECHNIQUE_TACTIC_RECORDS if item["id"] == record_id), None)
    if not target:
        return False
    MEMORY_TECHNIQUE_TACTIC_RECORDS.remove(target)
    return True


def footwork_identity_exists(identity):
    if using_database():
        row = fetch_one(
            """
            SELECT id FROM footwork_training
            WHERE athlete_id=%s AND training_date=%s AND footwork_dict_id=%s
              AND duration_minutes=%s AND set_count=%s AND IFNULL(note, '')=%s
            LIMIT 1
            """,
            identity,
        )
        return row is not None
    return identity in {_memory_footwork_identity(record) for record in MEMORY_FOOTWORK_RECORDS}


def list_footwork_records_by_athlete(athlete_id):
    return [record for record in list_footwork_records() if record["athlete_id"] == athlete_id]


def list_technique_records_by_athlete(athlete_id):
    return [record for record in list_technique_tactic_records() if record["athlete_id"] == athlete_id]


def _memory_footwork_identity(record):
    normalize_text = lambda value: " ".join(str(value or "").split())
    return (
        record["athlete_id"],
        record["training_date"],
        record["footwork_dict_id"],
        record["duration_minutes"],
        record["set_count"],
        normalize_text(record.get("note")),
    )


def _list_footwork_records_db(filters):
    clauses = []
    params = []
    if str(filters.get("athlete_id", "")).isdigit():
        clauses.append("ft.athlete_id = %s")
        params.append(int(filters["athlete_id"]))
    if filters.get("start_date"):
        clauses.append("ft.training_date >= %s")
        params.append(filters["start_date"])
    if filters.get("end_date"):
        clauses.append("ft.training_date <= %s")
        params.append(filters["end_date"])
    if str(filters.get("footwork_dict_id", "")).isdigit():
        clauses.append("ft.footwork_dict_id = %s")
        params.append(int(filters["footwork_dict_id"]))

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = fetch_all(
        f"""
        SELECT ft.*, a.name AS athlete_name
        FROM footwork_training ft
        JOIN athlete a ON ft.athlete_id = a.id
        {where_sql}
        ORDER BY ft.training_date DESC, ft.id DESC
        """,
        tuple(params),
    )
    records = [_row_to_footwork(row) for row in rows]
    keyword = str(filters.get("keyword", "")).strip().lower()
    if keyword:
        records = [
            record
            for record in records
            if keyword in record.get("athlete_name", "").lower()
            or keyword in record.get("note", "").lower()
            or keyword in (find_dict_by_id(record["footwork_dict_id"]) or {}).get("dict_name", "").lower()
        ]
    return records


def _technique_child_ids(category_id):
    return [item["id"] for item in get_dict_children("technique_tactic", category_id, leaf_only=True)]


def _apply_technique_category_filter(records, filters):
    if not str(filters.get("technique_category_id", "")).isdigit():
        return records
    if str(filters.get("technique_dict_id", "")).isdigit():
        return records
    child_ids = set(_technique_child_ids(int(filters["technique_category_id"])))
    if not child_ids:
        return []
    return [record for record in records if record["technique_dict_id"] in child_ids]


def _list_technique_tactic_records_db(filters):
    clauses = []
    params = []
    if str(filters.get("athlete_id", "")).isdigit():
        clauses.append("tt.athlete_id = %s")
        params.append(int(filters["athlete_id"]))
    if filters.get("start_date"):
        clauses.append("tt.training_date >= %s")
        params.append(filters["start_date"])
    if filters.get("end_date"):
        clauses.append("tt.training_date <= %s")
        params.append(filters["end_date"])
    if str(filters.get("technique_dict_id", "")).isdigit():
        clauses.append("tt.technique_dict_id = %s")
        params.append(int(filters["technique_dict_id"]))
    elif str(filters.get("technique_category_id", "")).isdigit():
        child_ids = _technique_child_ids(int(filters["technique_category_id"]))
        if child_ids:
            placeholders = ", ".join(["%s"] * len(child_ids))
            clauses.append(f"tt.technique_dict_id IN ({placeholders})")
            params.extend(child_ids)
        else:
            return []
    if filters.get("serve_frequency") in SERVE_FREQUENCY_OPTIONS:
        clauses.append("tt.serve_frequency = %s")
        params.append(filters["serve_frequency"])

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = fetch_all(
        f"""
        SELECT tt.*, a.name AS athlete_name
        FROM technique_tactic_training tt
        JOIN athlete a ON tt.athlete_id = a.id
        {where_sql}
        ORDER BY tt.training_date DESC, tt.id DESC
        """,
        tuple(params),
    )
    landing_map = _fetch_landing_items([row["id"] for row in rows])
    records = [_row_to_technique(row, landing_map.get(row["id"], [])) for row in rows]
    keyword = str(filters.get("keyword", "")).strip().lower()
    if keyword:
        filtered = []
        for record in records:
            technique = find_dict_by_id(record["technique_dict_id"]) or {}
            category = find_dict_by_id(technique.get("parent_id", 0)) or {}
            haystacks = [
                record.get("athlete_name", ""),
                record.get("qualitative_comment", ""),
                record.get("landing_distribution", ""),
                technique.get("dict_name", ""),
                category.get("dict_name", ""),
            ]
            if any(keyword in str(text).lower() for text in haystacks):
                filtered.append(record)
        records = filtered
    return records


def _list_footwork_records_memory(filters):
    records = list(MEMORY_FOOTWORK_RECORDS)
    if str(filters.get("athlete_id", "")).isdigit():
        athlete_id = int(filters["athlete_id"])
        records = [record for record in records if record["athlete_id"] == athlete_id]
    if filters.get("start_date"):
        records = [record for record in records if record["training_date"] >= filters["start_date"]]
    if filters.get("end_date"):
        records = [record for record in records if record["training_date"] <= filters["end_date"]]
    if str(filters.get("footwork_dict_id", "")).isdigit():
        footwork_dict_id = int(filters["footwork_dict_id"])
        records = [record for record in records if record["footwork_dict_id"] == footwork_dict_id]
    keyword = str(filters.get("keyword", "")).strip().lower()
    if keyword:
        records = [
            record
            for record in records
            if keyword in record.get("athlete_name", "").lower()
            or keyword in record.get("note", "").lower()
            or keyword in (find_dict_by_id(record["footwork_dict_id"]) or {}).get("dict_name", "").lower()
        ]
    records.sort(key=lambda item: (item["training_date"], item["id"]), reverse=True)
    return records


def _list_technique_tactic_records_memory(filters):
    records = list(MEMORY_TECHNIQUE_TACTIC_RECORDS)
    if str(filters.get("athlete_id", "")).isdigit():
        athlete_id = int(filters["athlete_id"])
        records = [record for record in records if record["athlete_id"] == athlete_id]
    if filters.get("start_date"):
        records = [record for record in records if record["training_date"] >= filters["start_date"]]
    if filters.get("end_date"):
        records = [record for record in records if record["training_date"] <= filters["end_date"]]
    if str(filters.get("technique_dict_id", "")).isdigit():
        technique_dict_id = int(filters["technique_dict_id"])
        records = [record for record in records if record["technique_dict_id"] == technique_dict_id]
    else:
        records = _apply_technique_category_filter(records, filters)
    if filters.get("serve_frequency") in SERVE_FREQUENCY_OPTIONS:
        records = [record for record in records if record["serve_frequency"] == filters["serve_frequency"]]
    keyword = str(filters.get("keyword", "")).strip().lower()
    if keyword:
        filtered = []
        for record in records:
            technique = find_dict_by_id(record["technique_dict_id"]) or {}
            category = find_dict_by_id(technique.get("parent_id", 0)) or {}
            haystacks = [
                record.get("athlete_name", ""),
                record.get("qualitative_comment", ""),
                record.get("landing_distribution", ""),
                technique.get("dict_name", ""),
                category.get("dict_name", ""),
            ]
            if any(keyword in str(text).lower() for text in haystacks):
                filtered.append(record)
        records = filtered
    records.sort(key=lambda item: (item["training_date"], item["id"]), reverse=True)
    return records


initialize_training_storage()
