from copy import deepcopy

import app as app_module
from app import app
from tests.helpers import csrf_data


def login(client, username="admin", password="admin123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def restore_state(original_plans, original_counter, original_items, original_item_counter):
    app_module.TRAINING_PLANS[:] = original_plans
    app_module.PLAN_ID_COUNTER = original_counter
    if hasattr(app_module, "TRAINING_PLAN_ITEMS"):
        app_module.TRAINING_PLAN_ITEMS[:] = original_items
    if hasattr(app_module, "PLAN_ITEM_ID_COUNTER"):
        app_module.PLAN_ITEM_ID_COUNTER = original_item_counter


def test_training_plan_creation_requires_at_least_one_executable_item():
    original_plans = deepcopy(app_module.TRAINING_PLANS)
    original_counter = app_module.PLAN_ID_COUNTER
    original_items = deepcopy(getattr(app_module, "TRAINING_PLAN_ITEMS", []))
    original_item_counter = getattr(app_module, "PLAN_ITEM_ID_COUNTER", 1)
    try:
        client = app.test_client()
        login(client)

        response = client.post(
            "/training/plans",
            data=csrf_data(
                client,
                {
                    "athlete_id": "1",
                    "coach_id": "1",
                    "plan_datetime": "2026-07-20T09:00",
                    "content": "没有拆分项目的计划",
                    "intensity": "中",
                    "duration": "60",
                    "location": "训练馆A",
                },
            ),
            follow_redirects=True,
        )

        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert len(app_module.TRAINING_PLANS) == len(original_plans)
        assert "至少添加一个训练计划项目" in body
    finally:
        restore_state(original_plans, original_counter, original_items, original_item_counter)


def test_training_plan_created_with_three_executable_module_items():
    original_plans = deepcopy(app_module.TRAINING_PLANS)
    original_counter = app_module.PLAN_ID_COUNTER
    original_items = deepcopy(getattr(app_module, "TRAINING_PLAN_ITEMS", []))
    original_item_counter = getattr(app_module, "PLAN_ITEM_ID_COUNTER", 1)
    try:
        client = app.test_client()
        login(client)

        response = client.post(
            "/training/plans",
            data=csrf_data(
                client,
                {
                    "athlete_id": "1",
                    "coach_id": "1",
                    "plan_datetime": "2026-07-20T09:00",
                    "content": "按模块拆分的训练计划",
                    "intensity": "中",
                    "duration": "90",
                    "location": "训练馆A",
                    "plan_status": "published",
                    "item_module_type": ["fitness", "footwork", "technique_tactic"],
                    "item_title": ["体能训练项目", "步法训练项目", "技战术训练项目"],
                    "item_target_description": ["体能目标", "步法目标", "技战术目标"],
                    "item_planned_sessions": ["2", "3", "4"],
                    "item_planned_minutes": ["30", "40", "50"],
                    "item_intensity": ["中", "中", "高"],
                },
            ),
            follow_redirects=True,
        )

        created_plan = app_module.TRAINING_PLANS[-1]
        created_items = [
            item
            for item in getattr(app_module, "TRAINING_PLAN_ITEMS", [])
            if item["plan_id"] == created_plan["id"]
        ]
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert len(created_items) == 3
        assert created_plan["status"] == "published"
        assert {item["module_type"] for item in created_items} == {"fitness", "footwork", "technique_tactic"}
        assert all(item["status"] == "pending" for item in created_items)
        assert "体能训练项目" in body
        assert "步法训练项目" in body
        assert "技战术训练项目" in body
    finally:
        restore_state(original_plans, original_counter, original_items, original_item_counter)


def test_training_plan_edit_form_exposes_status_and_can_update_it():
    original_plans = deepcopy(app_module.TRAINING_PLANS)
    original_counter = app_module.PLAN_ID_COUNTER
    original_items = deepcopy(getattr(app_module, "TRAINING_PLAN_ITEMS", []))
    original_item_counter = getattr(app_module, "PLAN_ITEM_ID_COUNTER", 1)
    try:
        client = app.test_client()
        login(client)

        plan = app_module.TRAINING_PLANS[0]
        plan["status"] = "draft"
        plan["plan_datetime"] = "2026-07-22 09:00"
        app_module.TRAINING_PLAN_ITEMS.append(
            {
                "id": 94001,
                "plan_id": plan["id"],
                "module_type": "fitness",
                "module_label": "体能训练",
                "item_title": "可发布计划项目",
                "target_description": "人工确认目标",
                "planned_sessions": 1,
                "planned_minutes": 30,
                "intensity": "中",
                "status": "pending",
            }
        )
        response = client.get(f"/training/plans/{plan['id']}/edit")
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "计划状态" in body
        assert 'option value="published"' in body

        response = client.post(
            f"/training/plans/{plan['id']}/edit",
            data=csrf_data(
                client,
                {
                    "athlete_id": str(plan["athlete_id"]),
                    "coach_id": str(plan["coach_id"]),
                    "plan_datetime": plan["plan_datetime"].replace(" ", "T"),
                    "content": plan["content"],
                    "intensity": plan["intensity"],
                    "duration": str(plan["duration"]),
                    "location": plan.get("location", ""),
                    "plan_status": "published",
                },
            ),
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert app_module.TRAINING_PLANS[0]["status"] == "published"
    finally:
        restore_state(original_plans, original_counter, original_items, original_item_counter)


def test_training_plan_cannot_be_published_without_executable_items():
    original_plans = deepcopy(app_module.TRAINING_PLANS)
    original_counter = app_module.PLAN_ID_COUNTER
    original_items = deepcopy(getattr(app_module, "TRAINING_PLAN_ITEMS", []))
    original_item_counter = getattr(app_module, "PLAN_ITEM_ID_COUNTER", 1)
    try:
        client = app.test_client()
        login(client)

        plan = app_module.TRAINING_PLANS[0]
        plan["status"] = "draft"
        plan["plan_datetime"] = "2026-07-22 09:00"
        app_module.TRAINING_PLAN_ITEMS[:] = [
            item for item in app_module.TRAINING_PLAN_ITEMS if item["plan_id"] != plan["id"]
        ]

        response = client.post(
            f"/training/plans/{plan['id']}/edit",
            data=csrf_data(
                client,
                {
                    "athlete_id": str(plan["athlete_id"]),
                    "coach_id": str(plan["coach_id"]),
                    "plan_datetime": plan["plan_datetime"].replace(" ", "T"),
                    "content": plan["content"],
                    "intensity": plan["intensity"],
                    "duration": str(plan["duration"]),
                    "location": plan.get("location", ""),
                    "plan_status": "published",
                },
            ),
            follow_redirects=True,
        )
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert app_module.TRAINING_PLANS[0]["status"] == "draft"
        assert "没有计划项目不能发布训练计划" in body
    finally:
        restore_state(original_plans, original_counter, original_items, original_item_counter)


def test_training_plan_cannot_be_completed_until_all_items_completed():
    original_plans = deepcopy(app_module.TRAINING_PLANS)
    original_counter = app_module.PLAN_ID_COUNTER
    original_items = deepcopy(getattr(app_module, "TRAINING_PLAN_ITEMS", []))
    original_item_counter = getattr(app_module, "PLAN_ITEM_ID_COUNTER", 1)
    try:
        client = app.test_client()
        login(client)

        plan = app_module.TRAINING_PLANS[0]
        plan["status"] = "running"
        plan["plan_datetime"] = "2026-07-22 09:00"
        app_module.TRAINING_PLAN_ITEMS[:] = [
            {
                "id": 95001,
                "plan_id": plan["id"],
                "module_type": "fitness",
                "module_label": "体能训练",
                "item_title": "已完成项目",
                "target_description": "完成目标",
                "planned_sessions": 1,
                "planned_minutes": 30,
                "intensity": "中",
                "status": "completed",
            },
            {
                "id": 95002,
                "plan_id": plan["id"],
                "module_type": "footwork",
                "module_label": "步法训练",
                "item_title": "待执行项目",
                "target_description": "待执行目标",
                "planned_sessions": 1,
                "planned_minutes": 30,
                "intensity": "中",
                "status": "pending",
            },
        ]

        response = client.post(
            f"/training/plans/{plan['id']}/edit",
            data=csrf_data(
                client,
                {
                    "athlete_id": str(plan["athlete_id"]),
                    "coach_id": str(plan["coach_id"]),
                    "plan_datetime": plan["plan_datetime"].replace(" ", "T"),
                    "content": plan["content"],
                    "intensity": plan["intensity"],
                    "duration": str(plan["duration"]),
                    "location": plan.get("location", ""),
                    "plan_status": "completed",
                },
            ),
            follow_redirects=True,
        )
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert app_module.TRAINING_PLANS[0]["status"] == "running"
        assert "所有计划项目完成后才能标记训练计划已完成" in body
    finally:
        restore_state(original_plans, original_counter, original_items, original_item_counter)
