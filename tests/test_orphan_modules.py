from copy import deepcopy

import app as app_module
from app import PLAYERS, app
from tests.helpers import csrf_data


def login(client, username="admin", password="admin123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def test_rehab_page_renders_tracking_ledger_and_risk_filter():
    client = app.test_client()
    login(client)

    response = client.get("/rehab/?risk_level=high")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "康复跟踪明细" in body
    assert "复训建议" in body
    assert "赵若溪" in body
    assert "王一鸣" not in body


def test_match_page_renders_statistics_and_result_filter():
    client = app.test_client()
    login(client)

    response = client.get("/matches/?result=负")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "比赛成绩统计" in body
    assert "胜率" in body
    assert "陈昊然" in body
    assert "王一鸣" in body


def test_match_record_can_be_edited():
    original_matches = deepcopy(app_module.MATCH_RESULTS)
    try:
        client = app.test_client()
        login(client)
        record_id = app_module.MATCH_RESULTS[0]["id"]

        edit_page = client.get(f"/matches/?edit_id={record_id}")
        edit_body = edit_page.get_data(as_text=True)

        assert edit_page.status_code == 200
        assert "修改比赛成绩" in edit_body
        assert app_module.MATCH_RESULTS[0]["match_name"] in edit_body

        response = client.post(
            "/matches/",
            data=csrf_data(
                client,
                {
                    "record_id": str(record_id),
                    "athlete_id": str(PLAYERS[1]["id"]),
                    "match_type": "友谊赛",
                    "opponent_source": "internal",
                    "opponent_id": str(PLAYERS[2]["id"]),
                    "match_date": "2026-07-20",
                    "match_name": "修改后的比赛",
                    "result": "胜",
                    "score": "3:0",
                    "rank": "冠军",
                    "key_points": "关键分修改",
                    "tactic_review": "战术复盘修改",
                    "improvement": "改进方向修改",
                },
            ),
            follow_redirects=True,
        )

        updated = next(item for item in app_module.MATCH_RESULTS if item["id"] == record_id)
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert updated["athlete_id"] == PLAYERS[1]["id"]
        assert updated["match_type"] == "友谊赛"
        assert updated["opponent_source"] == "internal"
        assert updated["opponent_id"] == PLAYERS[2]["id"]
        assert updated["match_name"] == "修改后的比赛"
        assert updated["opponent"] == PLAYERS[2]["name"]
        assert updated["score"] == "3:0"
        assert "比赛成绩已更新" in body
    finally:
        app_module.MATCH_RESULTS[:] = original_matches


def test_internal_opponent_match_record_can_be_created():
    original_matches = deepcopy(app_module.MATCH_RESULTS)
    try:
        client = app.test_client()
        login(client)

        response = client.post(
            "/matches/",
            data=csrf_data(
                client,
                {
                    "athlete_id": str(PLAYERS[0]["id"]),
                    "match_type": "友谊赛",
                    "opponent_source": "internal",
                    "opponent_id": str(PLAYERS[1]["id"]),
                    "match_date": "2026-07-21",
                    "match_name": "新增比赛",
                    "result": "负",
                    "score": "1:3",
                    "rank": "小组赛",
                    "key_points": "新增关键分",
                    "tactic_review": "新增复盘",
                    "improvement": "新增改进",
                },
            ),
            follow_redirects=True,
        )

        body = response.get_data(as_text=True)
        created = app_module.MATCH_RESULTS[-1]

        assert response.status_code == 200
        assert len(app_module.MATCH_RESULTS) == len(original_matches) + 1
        assert created["match_name"] == "新增比赛"
        assert created["athlete_id"] == PLAYERS[0]["id"]
        assert created["match_type"] == "友谊赛"
        assert created["opponent_source"] == "internal"
        assert created["opponent_id"] == PLAYERS[1]["id"]
        assert created["opponent"] == PLAYERS[1]["name"]
        assert "比赛成绩已保存" in body
    finally:
        app_module.MATCH_RESULTS[:] = original_matches


def test_external_opponent_match_record_can_be_created():
    original_matches = deepcopy(app_module.MATCH_RESULTS)
    try:
        client = app.test_client()
        login(client)

        response = client.post(
            "/matches/",
            data=csrf_data(
                client,
                {
                    "athlete_id": str(PLAYERS[0]["id"]),
                    "match_type": "正式比赛",
                    "opponent_source": "external",
                    "opponent_external_name": "外部选手A",
                    "match_date": "2026-07-22",
                    "match_name": "市级公开赛",
                    "result": "胜",
                    "score": "3:2",
                    "rank": "决赛",
                    "key_points": "外部对手关键分",
                    "tactic_review": "外部对手复盘",
                    "improvement": "外部对手改进",
                },
            ),
            follow_redirects=True,
        )

        body = response.get_data(as_text=True)
        created = app_module.MATCH_RESULTS[-1]

        assert response.status_code == 200
        assert len(app_module.MATCH_RESULTS) == len(original_matches) + 1
        assert created["match_type"] == "正式比赛"
        assert created["opponent_source"] == "external"
        assert created["opponent_id"] is None
        assert created["opponent"] == "外部选手A"
        assert "比赛成绩已保存" in body
    finally:
        app_module.MATCH_RESULTS[:] = original_matches


def test_match_record_rejects_same_player_as_opponent():
    original_matches = deepcopy(app_module.MATCH_RESULTS)
    try:
        client = app.test_client()
        login(client)

        response = client.post(
            "/matches/",
            data=csrf_data(
                client,
                {
                    "athlete_id": str(PLAYERS[0]["id"]),
                    "match_type": "友谊赛",
                    "opponent_source": "internal",
                    "opponent_id": str(PLAYERS[0]["id"]),
                    "match_date": "2026-07-21",
                    "match_name": "同人比赛",
                    "result": "胜",
                    "score": "3:0",
                },
            ),
            follow_redirects=True,
        )

        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert len(app_module.MATCH_RESULTS) == len(original_matches)
        assert "对手不能与运动员相同" in body
    finally:
        app_module.MATCH_RESULTS[:] = original_matches


def test_match_record_rejects_blank_external_opponent_name():
    original_matches = deepcopy(app_module.MATCH_RESULTS)
    try:
        client = app.test_client()
        login(client)

        response = client.post(
            "/matches/",
            data=csrf_data(
                client,
                {
                    "athlete_id": str(PLAYERS[0]["id"]),
                    "match_type": "正式比赛",
                    "opponent_source": "external",
                    "opponent_external_name": "   ",
                    "match_date": "2026-07-21",
                    "match_name": "外部空对手",
                    "result": "胜",
                    "score": "3:0",
                },
            ),
            follow_redirects=True,
        )

        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert len(app_module.MATCH_RESULTS) == len(original_matches)
        assert "系统外对手姓名不能为空" in body
    finally:
        app_module.MATCH_RESULTS[:] = original_matches


def test_auth_page_renders_permission_matrix_and_database_accounts():
    client = app.test_client()
    login(client)

    response = client.get("/auth/users")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "权限矩阵" in body
    assert "coach_app" in body
    assert "训练数据录入" in body


def test_coach_cannot_open_permission_management():
    client = app.test_client()
    login(client, "coach", "user123")

    response = client.get("/auth/users")

    assert response.status_code == 403


def test_settings_page_renders_dictionary_and_database_health_checks():
    client = app.test_client()
    login(client)

    response = client.get("/settings/dictionary")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "系统运行检查" in body
    assert "pingpang_db" in body
    assert "视图" in body
    assert "存储过程" in body
