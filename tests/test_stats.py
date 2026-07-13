import io
from copy import deepcopy

import openpyxl

import app as app_module
from app import FOOTWORK_TRAINING_RECORDS, app
from tests.helpers import csrf_data


def login(client, username="admin", password="admin123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def test_stats_dashboard_renders_charts_and_cards():
    client = app.test_client()
    login(client)

    response = client.get("/stats/dashboard")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "数据统计看板" in body
    assert "月度训练时长趋势" in body
    assert "伤病部位分布" in body
    assert "trainTrendChart" in body


def test_stats_export_all_returns_xlsx_workbook():
    client = app.test_client()
    login(client)

    response = client.get("/stats/export/all")

    assert response.status_code == 200
    assert response.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    workbook = openpyxl.load_workbook(io.BytesIO(response.data))
    assert workbook.sheetnames == ["训练计划", "步法训练记录", "技战术训练记录", "体能测试记录", "伤病记录"]


def test_stats_import_accepts_member9_skill_excel_format():
    client = app.test_client()
    login(client)

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["运动员姓名", "训练日期", "步法时长", "击球得分", "多球时长", "训练强度"])
    sheet.append(["王一鸣", "2026-07-09", 45, 88, 30, "高"])
    payload = io.BytesIO()
    workbook.save(payload)
    payload.seek(0)

    before_count = len(FOOTWORK_TRAINING_RECORDS)
    try:
        response = client.post(
            "/stats/import-export",
            data=csrf_data(
                client,
                {
                    "action": "import_skill",
                    "skill_excel": (payload, "member9_skill.xlsx"),
                },
            ),
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert len(FOOTWORK_TRAINING_RECORDS) == before_count + 1
        imported = FOOTWORK_TRAINING_RECORDS[-1]
        assert imported["athlete_name"] == "王一鸣"
        assert imported["training_date"] == "2026-07-09"
        assert imported["duration_minutes"] == 45
    finally:
        del FOOTWORK_TRAINING_RECORDS[before_count:]


def test_stats_import_creates_player_archive_for_new_names():
    client = app.test_client()
    login(client)

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["运动员姓名", "训练日期", "步法时长", "击球得分", "多球时长", "训练强度"])
    sheet.append(["小红", "2026-06-09", 27, 82, 27, "低"])
    payload = io.BytesIO()
    workbook.save(payload)
    payload.seek(0)

    original_players = deepcopy(app_module.PLAYERS)
    before_count = len(FOOTWORK_TRAINING_RECORDS)
    try:
        response = client.post(
            "/stats/import-export",
            data=csrf_data(
                client,
                {
                    "action": "import_skill",
                    "skill_excel": (payload, "member9_skill_new_player.xlsx"),
                },
            ),
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        created_player = next((player for player in app_module.PLAYERS if player["name"] == "小红"), None)
        imported = FOOTWORK_TRAINING_RECORDS[-1]

        assert response.status_code == 200
        assert created_player is not None
        assert created_player["student_no"].startswith("IMP")
        assert len(FOOTWORK_TRAINING_RECORDS) == before_count + 1
        assert imported["athlete_id"] == created_player["id"]
        assert imported["athlete_name"] == "小红"
    finally:
        app_module.PLAYERS[:] = original_players
        del FOOTWORK_TRAINING_RECORDS[before_count:]
