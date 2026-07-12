from copy import deepcopy
import io

import openpyxl
import app as app_module
from app import PLAYERS, app
from tests.helpers import csrf_data


def login(client, username="admin", password="admin123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def get_training_records():
    return getattr(app_module, "TECHNICAL_TRAINING_RECORDS", [])


def test_specialized_training_records_support_crud_and_complex_filters():
    original_records = deepcopy(get_training_records())
    try:
        client = app.test_client()
        login(client)

        create_response = client.post(
            "/training/batch-import",
            data=csrf_data(
                client,
                {
                    "athlete_id": "3",
                    "training_date": "2026-07-08",
                    "footwork_type": "cross_step",
                    "stroke_technique": "smash",
                    "multi_ball_minutes": "35",
                    "intensity": "high",
                    "training_note": "precision footwork note",
                },
            ),
            follow_redirects=True,
        )

        records = get_training_records()
        assert create_response.status_code == 200
        assert len(records) == len(original_records) + 1
        record_id = records[-1]["id"]
        assert records[-1]["athlete_id"] == 3

        filtered_response = client.get(
            "/training/records"
            "?athlete_id=3"
            "&start_date=2026-07-01"
            "&end_date=2026-07-31"
            "&footwork_type=cross_step"
            "&stroke_technique=smash"
            "&intensity=high"
            "&minutes_min=30"
            "&minutes_max=40"
            "&keyword=precision"
        )
        filtered_body = filtered_response.get_data(as_text=True)

        assert filtered_response.status_code == 200
        assert "precision footwork note" in filtered_body
        assert "2026-07-08" in filtered_body

        edit_page = client.get(f"/training/batch-import?edit_id={record_id}")
        assert edit_page.status_code == 200
        assert "precision footwork note" in edit_page.get_data(as_text=True)

        edit_response = client.post(
            f"/training/records/{record_id}/edit",
            data=csrf_data(
                client,
                {
                    "athlete_id": "3",
                    "training_date": "2026-07-09",
                    "footwork_type": "composite",
                    "stroke_technique": "serve_receive",
                    "multi_ball_minutes": "45",
                    "intensity": "medium",
                    "training_note": "updated record note",
                },
            ),
            follow_redirects=True,
        )

        assert edit_response.status_code == 200
        assert records[-1]["training_date"] == "2026-07-09"
        assert records[-1]["multi_ball_minutes"] == 45

        delete_response = client.post(
            f"/training/records/{record_id}/delete",
            data=csrf_data(client),
            follow_redirects=True,
        )

        assert delete_response.status_code == 200
        assert all(record["id"] != record_id for record in get_training_records())
    finally:
        records = get_training_records()
        records[:] = original_records


def test_training_record_form_uses_current_player_list():
    client = app.test_client()
    login(client)

    response = client.get("/training/batch-import")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert PLAYERS[-1]["name"] in body


def test_skill_excel_import_accepts_player_name_and_student_no():
    original_records = deepcopy(get_training_records())
    try:
        client = app.test_client()
        login(client)

        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["运动员编号或姓名", "训练日期", "步法类型", "击球技术", "多球时长", "训练强度", "备注"])
        sheet.append([PLAYERS[0]["name"], "2026-07-10", "交叉步", "扣杀", 30, "高强度", "name import"])
        sheet.append([PLAYERS[1]["student_no"], "2026-07-11", "综合步法", "发接发", 35, "中强度", "student import"])
        payload = io.BytesIO()
        workbook.save(payload)
        payload.seek(0)

        response = client.post(
            "/training/records/import-excel",
            data=csrf_data(
                client,
                {"training_excel": (payload, "skill_import.xlsx")},
            ),
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        body = response.get_data(as_text=True)
        records = get_training_records()

        assert response.status_code == 200
        assert "成功导入 2 条专项技术记录" in body
        assert len(records) == len(original_records) + 2
        assert records[-2]["athlete_id"] == PLAYERS[0]["id"]
        assert records[-1]["athlete_id"] == PLAYERS[1]["id"]
    finally:
        records = get_training_records()
        records[:] = original_records
