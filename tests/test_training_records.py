from copy import deepcopy
import io

import openpyxl
import app as app_module
from app import FOOTWORK_TRAINING_RECORDS, PLAYERS, TECHNIQUE_TACTIC_TRAINING_RECORDS, app, find_dict_by_code
from tests.helpers import csrf_data


def login(client, username="admin", password="admin123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def test_footwork_training_supports_crud_and_filters():
    original_records = deepcopy(FOOTWORK_TRAINING_RECORDS)
    try:
        client = app.test_client()
        login(client)
        footwork_dict_id = find_dict_by_code("cross_step")["id"]

        create_response = client.post(
            "/training/footwork",
            data=csrf_data(
                client,
                {
                    "athlete_id": "3",
                    "training_date": "2026-07-08",
                    "footwork_dict_id": str(footwork_dict_id),
                    "duration_minutes": "35",
                    "set_count": "6",
                    "training_note": "precision footwork note",
                },
            ),
            follow_redirects=True,
        )

        assert create_response.status_code == 200
        assert len(FOOTWORK_TRAINING_RECORDS) == len(original_records) + 1
        record_id = FOOTWORK_TRAINING_RECORDS[-1]["id"]
        assert FOOTWORK_TRAINING_RECORDS[-1]["athlete_id"] == 3

        edit_response = client.post(
            f"/training/footwork/{record_id}/edit",
            data=csrf_data(
                client,
                {
                    "athlete_id": "3",
                    "training_date": "2026-07-09",
                    "footwork_dict_id": str(find_dict_by_code("composite_step")["id"]),
                    "duration_minutes": "45",
                    "set_count": "8",
                    "training_note": "updated footwork note",
                },
            ),
            follow_redirects=True,
        )

        assert edit_response.status_code == 200
        assert FOOTWORK_TRAINING_RECORDS[-1]["training_date"] == "2026-07-09"
        assert FOOTWORK_TRAINING_RECORDS[-1]["duration_minutes"] == 45

        delete_response = client.post(
            f"/training/footwork/{record_id}/delete",
            data=csrf_data(client),
            follow_redirects=True,
        )

        assert delete_response.status_code == 200
        assert all(record["id"] != record_id for record in FOOTWORK_TRAINING_RECORDS)

        filtered_response = client.get(
            "/training/footwork"
            "?athlete_id=3"
            "&start_date=2026-07-01"
            "&end_date=2026-07-31"
            "&keyword=precision"
        )
        filtered_body = filtered_response.get_data(as_text=True)
        assert filtered_response.status_code == 200
        assert "筛选条件" in filtered_body
        assert "记录列表" in filtered_body
    finally:
        FOOTWORK_TRAINING_RECORDS[:] = original_records


def test_technique_tactic_training_supports_form_list_and_filters():
    original_records = deepcopy(TECHNIQUE_TACTIC_TRAINING_RECORDS)
    try:
        client = app.test_client()
        login(client)
        technique_dict_id = find_dict_by_code("forehand_smash")["id"]
        near_left_id = find_dict_by_code("near_left")["id"]

        create_response = client.post(
            "/training/technique-tactic",
            data=csrf_data(
                client,
                {
                    "athlete_id": "3",
                    "training_date": "2026-07-08",
                    "technique_dict_id": str(technique_dict_id),
                    "multi_ball_count": "400",
                    "serve_frequency": "高",
                    "plan_execution_rate": "88",
                    "on_table_rate": "82",
                    f"landing_concentration_{near_left_id}": "较为集中",
                    "qualitative_comment": "precision tactic note",
                },
            ),
            follow_redirects=True,
        )

        body = create_response.get_data(as_text=True)
        assert create_response.status_code == 200
        assert len(TECHNIQUE_TACTIC_TRAINING_RECORDS) == len(original_records) + 1
        assert "近台左侧（较为集中）" in body

        filtered_response = client.get(
            "/training/technique-tactic"
            "?athlete_id=3"
            "&start_date=2026-07-01"
            "&end_date=2026-07-31"
            "&serve_frequency=高"
            "&keyword=precision"
        )
        filtered_body = filtered_response.get_data(as_text=True)
        assert filtered_response.status_code == 200
        assert "precision tactic note" in filtered_body
    finally:
        TECHNIQUE_TACTIC_TRAINING_RECORDS[:] = original_records


def test_footwork_form_uses_current_player_list():
    client = app.test_client()
    login(client)

    response = client.get("/training/footwork")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert PLAYERS[-1]["name"] in body
    assert "步法训练" in body


def test_technique_tactic_list_supports_pagination_with_filters():
    original_records = deepcopy(TECHNIQUE_TACTIC_TRAINING_RECORDS)
    try:
        TECHNIQUE_TACTIC_TRAINING_RECORDS[:] = []
        technique_dict_id = find_dict_by_code("forehand_smash")["id"]
        mid_table_id = find_dict_by_code("mid_table")["id"]
        for index in range(12):
            TECHNIQUE_TACTIC_TRAINING_RECORDS.append(
                {
                    "id": index + 1,
                    "athlete_id": PLAYERS[0]["id"],
                    "athlete_name": PLAYERS[0]["name"],
                    "training_date": f"2026-07-{index + 1:02d}",
                    "technique_dict_id": technique_dict_id,
                    "multi_ball_count": 300 + index,
                    "serve_frequency": "高",
                    "plan_execution_rate": 80 + index,
                    "on_table_rate": 75 + index,
                    "landing_distribution_items": [{"landing_dict_id": mid_table_id, "concentration": "较为集中"}],
                    "landing_distribution": "中台（较为集中）",
                    "qualitative_comment": f"pagination note {index + 1}",
                    "created_by": "admin",
                }
            )

        client = app.test_client()
        login(client)
        response = client.get("/training/technique-tactic?serve_frequency=高&page=2")
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "pagination note 2" in body
        assert "pagination note 12" not in body
        assert "第 2 / 2 页" in body
    finally:
        TECHNIQUE_TACTIC_TRAINING_RECORDS[:] = original_records


def test_footwork_excel_import_accepts_new_template():
    original_records = deepcopy(FOOTWORK_TRAINING_RECORDS)
    try:
        client = app.test_client()
        login(client)

        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["运动员学号", "训练日期", "步法类型", "训练时长(分钟)", "训练组数", "训练备注"])
        sheet.append([PLAYERS[0]["student_no"], "2026-07-10", "交叉步", 30, 5, "student import"])
        sheet.append([PLAYERS[1]["student_no"], "2026-07-11", "综合步法", 35, 6, "second import"])
        payload = io.BytesIO()
        workbook.save(payload)
        payload.seek(0)

        response = client.post(
            "/training/footwork/import-excel",
            data=csrf_data(client, {"training_excel": (payload, "footwork_import.xlsx")}),
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        body = response.get_data(as_text=True)
        assert response.status_code == 200
        assert "成功导入 2 条步法训练记录" in body
        assert len(FOOTWORK_TRAINING_RECORDS) == len(original_records) + 2
    finally:
        FOOTWORK_TRAINING_RECORDS[:] = original_records


def test_footwork_excel_import_skips_duplicate_rows():
    original_records = deepcopy(FOOTWORK_TRAINING_RECORDS)
    try:
        client = app.test_client()
        login(client)

        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["运动员学号", "训练日期", "步法类型", "训练时长(分钟)", "训练组数", "训练备注"])
        duplicate_row = [PLAYERS[0]["student_no"], "2026-07-10", "交叉步", 30, 5, "same file duplicate"]
        sheet.append(duplicate_row)
        sheet.append(duplicate_row)
        payload = io.BytesIO()
        workbook.save(payload)
        payload.seek(0)

        response = client.post(
            "/training/footwork/import-excel",
            data=csrf_data(client, {"training_excel": (payload, "footwork_import.xlsx")}),
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        body = response.get_data(as_text=True)
        assert response.status_code == 200
        assert len(FOOTWORK_TRAINING_RECORDS) == len(original_records) + 1
        assert "第 3 行：重复步法训练记录已跳过" in body
    finally:
        FOOTWORK_TRAINING_RECORDS[:] = original_records
