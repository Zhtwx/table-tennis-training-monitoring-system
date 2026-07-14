from copy import deepcopy

import app as app_module
from app import app
from pymysql import MySQLError


def login(client, username="admin", password="admin123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def test_fitness_training_frame_is_available_and_keeps_legacy_tests_link():
    client = app.test_client()
    login(client)

    response = client.get("/fitness/training")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "体能训练" in body
    assert "待执行" in body
    assert "历史体能测试" in body
    assert "/fitness/tests" in body


def test_fitness_training_frame_reuses_historical_fitness_sync_data_when_no_plan_items():
    original_items = deepcopy(app_module.TRAINING_PLAN_ITEMS)
    try:
        app_module.TRAINING_PLAN_ITEMS[:] = []

        client = app.test_client()
        login(client)
        response = client.get("/fitness/training")
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "来自历史体能测试同步" in body
        assert "体能巩固训练" in body
        assert "速度敏捷提升" in body
        assert "恢复拉伸结合耐力课" in body
        assert "康复过渡训练" in body
        assert "近期体能复测待安排" in body
        assert "暂无待执行体能训练项目" not in body
    finally:
        app_module.TRAINING_PLAN_ITEMS[:] = original_items


def test_fitness_training_frame_prefers_sql_fitness_training_records(monkeypatch):
    original_items = deepcopy(app_module.TRAINING_PLAN_ITEMS)
    try:
        app_module.TRAINING_PLAN_ITEMS[:] = []
        monkeypatch.setenv("TRAINING_STORAGE", "mysql")

        def fake_fetch_all(query, params=None):
            assert "fitness_training_record" in query
            return [
                {
                    "id": 1,
                    "athlete_name": "SQL运动员",
                    "test_date": "2026-07-12 09:00",
                    "plan_name": "SQL体能速度课",
                    "training_hours": 1.5,
                    "training_intensity": "中",
                    "plan_status": "进行中",
                    "overall_score": 8.2,
                    "notes": "来自数据库的体能训练记录",
                }
            ]

        monkeypatch.setattr(app_module, "fetch_all", fake_fetch_all)

        client = app.test_client()
        login(client)
        response = client.get("/fitness/training")
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "SQL体能速度课" in body
        assert "SQL运动员" in body
        assert "来自数据库体能训练记录" in body
        assert "体能巩固训练" not in body
    finally:
        app_module.TRAINING_PLAN_ITEMS[:] = original_items


def test_fitness_training_frame_falls_back_to_sql_fitness_reports(monkeypatch):
    original_items = deepcopy(app_module.TRAINING_PLAN_ITEMS)
    calls = []
    try:
        app_module.TRAINING_PLAN_ITEMS[:] = []
        monkeypatch.setenv("TRAINING_STORAGE", "mysql")

        def fake_fetch_all(query, params=None):
            calls.append(query)
            if "fitness_training_record" in query:
                raise MySQLError(1146, "fitness_training_record does not exist")
            assert "fitness_report" in query
            return [
                {
                    "id": 2,
                    "athlete_name": "基础库运动员",
                    "test_date": "2026-07-01",
                    "plan_name": "基础库体测关联训练",
                    "training_hours": 2.0,
                    "training_intensity": "低",
                    "plan_status": "待执行",
                    "overall_score": 75.2,
                    "notes": "来自 pingpang_db.sql 的体测数据",
                }
            ]

        monkeypatch.setattr(app_module, "fetch_all", fake_fetch_all)

        client = app.test_client()
        login(client)
        response = client.get("/fitness/training")
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "基础库体测关联训练" in body
        assert "基础库运动员" in body
        assert "来自数据库历史体能测试" in body
    finally:
        app_module.TRAINING_PLAN_ITEMS[:] = original_items


def test_navigation_points_fitness_training_to_new_frame():
    client = app.test_client()
    login(client)

    response = client.get("/matches/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'href="/fitness/training"' in body
    assert 'href="/fitness/tests"' not in body


def test_fitness_training_frame_only_lists_fitness_plan_items():
    original_items = deepcopy(app_module.TRAINING_PLAN_ITEMS)
    original_plans = deepcopy(app_module.TRAINING_PLANS)
    try:
        plan_id = app_module.TRAINING_PLANS[0]["id"]
        app_module.TRAINING_PLANS[0]["status"] = "published"
        app_module.TRAINING_PLAN_ITEMS[:] = [
            {
                "id": 9001,
                "plan_id": plan_id,
                "module_type": "fitness",
                "module_label": "体能训练",
                "item_title": "体能专项待执行",
                "target_description": "体能目标",
                "planned_sessions": 2,
                "planned_minutes": 30,
                "intensity": "中",
                "status": "pending",
            },
            {
                "id": 9002,
                "plan_id": plan_id,
                "module_type": "footwork",
                "module_label": "步法训练",
                "item_title": "步法专项待执行",
                "target_description": "步法目标",
                "planned_sessions": 2,
                "planned_minutes": 30,
                "intensity": "中",
                "status": "pending",
            },
        ]

        client = app.test_client()
        login(client)
        response = client.get("/fitness/training")
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "体能专项待执行" in body
        assert "步法专项待执行" not in body
    finally:
        app_module.TRAINING_PLAN_ITEMS[:] = original_items
        app_module.TRAINING_PLANS[:] = original_plans


def test_execution_frames_do_not_list_draft_plan_items():
    original_items = deepcopy(app_module.TRAINING_PLAN_ITEMS)
    original_plans = deepcopy(app_module.TRAINING_PLANS)
    try:
        app_module.TRAINING_PLANS[:] = [
            {
                "id": 9301,
                "athlete_id": 1,
                "athlete_name": "王一鸣",
                "coach_id": 1,
                "coach_name": "张教练",
                "plan_datetime": "2026-07-22 09:00",
                "content": "草稿计划不应下发",
                "intensity": "中",
                "duration": 60,
                "location": "训练馆A",
                "status": "draft",
            },
            {
                "id": 9302,
                "athlete_id": 1,
                "athlete_name": "王一鸣",
                "coach_id": 1,
                "coach_name": "张教练",
                "plan_datetime": "2026-07-23 09:00",
                "content": "已发布计划应下发",
                "intensity": "中",
                "duration": 60,
                "location": "训练馆A",
                "status": "published",
            },
        ]
        app_module.TRAINING_PLAN_ITEMS[:] = [
            {
                "id": 93011,
                "plan_id": 9301,
                "module_type": "fitness",
                "module_label": "体能训练",
                "item_title": "草稿体能项目",
                "target_description": "草稿目标",
                "planned_sessions": 2,
                "planned_minutes": 30,
                "intensity": "中",
                "status": "pending",
            },
            {
                "id": 93021,
                "plan_id": 9302,
                "module_type": "fitness",
                "module_label": "体能训练",
                "item_title": "已发布体能项目",
                "target_description": "发布目标",
                "planned_sessions": 2,
                "planned_minutes": 30,
                "intensity": "中",
                "status": "pending",
            },
        ]

        client = app.test_client()
        login(client)
        response = client.get("/fitness/training")
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "已发布体能项目" in body
        assert "草稿体能项目" not in body
    finally:
        app_module.TRAINING_PLAN_ITEMS[:] = original_items
        app_module.TRAINING_PLANS[:] = original_plans


def test_footwork_page_only_lists_footwork_plan_items():
    original_items = deepcopy(app_module.TRAINING_PLAN_ITEMS)
    try:
        plan_id = app_module.TRAINING_PLANS[0]["id"]
        app_module.TRAINING_PLAN_ITEMS[:] = [
            {
                "id": 9101,
                "plan_id": plan_id,
                "module_type": "footwork",
                "module_label": "步法训练",
                "item_title": "步法计划项目提示",
                "target_description": "步法目标",
                "planned_sessions": 2,
                "planned_minutes": 30,
                "intensity": "中",
                "status": "pending",
            },
            {
                "id": 9102,
                "plan_id": plan_id,
                "module_type": "fitness",
                "module_label": "体能训练",
                "item_title": "体能计划项目不应出现",
                "target_description": "体能目标",
                "planned_sessions": 2,
                "planned_minutes": 30,
                "intensity": "中",
                "status": "pending",
            },
        ]

        client = app.test_client()
        login(client)
        response = client.get("/training/footwork")
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "计划项目提示" in body
        assert "步法计划项目提示" in body
        assert "体能计划项目不应出现" not in body
    finally:
        app_module.TRAINING_PLAN_ITEMS[:] = original_items


def test_technique_tactic_page_only_lists_technique_tactic_plan_items():
    original_items = deepcopy(app_module.TRAINING_PLAN_ITEMS)
    try:
        plan_id = app_module.TRAINING_PLANS[0]["id"]
        app_module.TRAINING_PLAN_ITEMS[:] = [
            {
                "id": 9201,
                "plan_id": plan_id,
                "module_type": "technique_tactic",
                "module_label": "技战术训练",
                "item_title": "技战术计划项目提示",
                "target_description": "技战术目标",
                "planned_sessions": 2,
                "planned_minutes": 30,
                "intensity": "高",
                "status": "pending",
            },
            {
                "id": 9202,
                "plan_id": plan_id,
                "module_type": "footwork",
                "module_label": "步法训练",
                "item_title": "步法计划项目不应出现",
                "target_description": "步法目标",
                "planned_sessions": 2,
                "planned_minutes": 30,
                "intensity": "中",
                "status": "pending",
            },
        ]

        client = app.test_client()
        login(client)
        response = client.get("/training/technique-tactic")
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "计划项目提示" in body
        assert "技战术计划项目提示" in body
        assert "步法计划项目不应出现" not in body
    finally:
        app_module.TRAINING_PLAN_ITEMS[:] = original_items
