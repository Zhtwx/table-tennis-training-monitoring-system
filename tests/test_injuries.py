from copy import deepcopy

import pytest

from app import INJURY_FOLLOWUPS, INJURY_RECORDS, PLAYERS, app
from tests.helpers import csrf_data


@pytest.fixture(autouse=True)
def restore_demo_data():
    original_players = deepcopy(PLAYERS)
    original_injuries = deepcopy(INJURY_RECORDS)
    original_followups = deepcopy(INJURY_FOLLOWUPS)
    yield
    PLAYERS[:] = original_players
    INJURY_RECORDS[:] = original_injuries
    INJURY_FOLLOWUPS[:] = original_followups


@pytest.fixture()
def admin_client():
    client = app.test_client()
    client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )
    return client


@pytest.fixture()
def coach_client():
    client = app.test_client()
    client.post(
        "/login",
        data={"username": "coach", "password": "user123"},
        follow_redirects=True,
    )
    return client


def injury_payload(**overrides):
    data = {
        "action": "save",
        "athlete_id": "1",
        "injury_date": "2026-07-08",
        "injury_location": "右肘",
        "injury_type": "拉伤",
        "severity": "轻微",
        "recovery_status": "治疗中",
        "expected_recovery_date": "2026-07-20",
        "diagnosis": "测试诊断",
        "treatment": "测试处理",
        "notes": "测试备注",
    }
    data.update(overrides)
    return data


def test_injury_list_page_renders(admin_client):
    response = admin_client.get("/injuries/")

    assert response.status_code == 200
    assert "伤病记录模块" in response.get_data(as_text=True)


def test_invalid_record_id_is_rejected(admin_client):
    before_count = len(INJURY_RECORDS)

    response = admin_client.post(
        "/injuries/",
        data=csrf_data(admin_client, injury_payload(record_id="abc")),
        follow_redirects=True,
    )

    assert len(INJURY_RECORDS) == before_count
    assert "伤病记录编号非法" in response.get_data(as_text=True)


def test_admin_can_register_serious_injury_and_refresh_status(admin_client):
    before_count = len(INJURY_RECORDS)

    admin_client.post(
        "/injuries/",
        data=csrf_data(
            admin_client,
            injury_payload(severity="严重", recovery_status="治疗中"),
        ),
        follow_redirects=True,
    )

    assert len(INJURY_RECORDS) == before_count + 1
    assert next(player for player in PLAYERS if player["id"] == 1)["injury_status"] == "伤病中"


def test_coach_cannot_register_serious_or_recovered_record(coach_client):
    before_count = len(INJURY_RECORDS)

    serious_response = coach_client.post(
        "/injuries/",
        data=csrf_data(coach_client, injury_payload(severity="严重")),
        follow_redirects=True,
    )
    recovered_response = coach_client.post(
        "/injuries/",
        data=csrf_data(coach_client, injury_payload(recovery_status="已恢复")),
        follow_redirects=True,
    )

    assert len(INJURY_RECORDS) == before_count
    assert "严重伤病需管理员确认" in serious_response.get_data(as_text=True)
    assert "恢复完成状态需管理员确认" in recovered_response.get_data(as_text=True)


def test_archive_record_excludes_it_from_status(admin_client):
    admin_client.post(
        "/injuries/",
        data=csrf_data(
            admin_client,
            injury_payload(severity="严重", recovery_status="治疗中"),
        ),
        follow_redirects=True,
    )
    record_id = INJURY_RECORDS[-1]["id"]

    admin_client.post(
        "/injuries/",
        data=csrf_data(
            admin_client,
            {
                "action": "archive",
                "archive_record_id": str(record_id),
                "delete_reason": "测试作废",
            },
        ),
        follow_redirects=True,
    )

    assert INJURY_RECORDS[-1]["is_deleted"] is True
    assert next(player for player in PLAYERS if player["id"] == 1)["injury_status"] == "健康"


def test_followup_validation_and_history_render(admin_client):
    response = admin_client.post(
        "/injuries/",
        data=csrf_data(
            admin_client,
            {
                "action": "followup",
                "followup_record_id": "2",
                "followup_date": "2026-07-03",
                "pain_score": "2",
                "training_limit": "降低反手训练量",
                "advice": "继续观察",
                "reviewer": "刘指导",
            },
        ),
        follow_redirects=True,
    )
    history = admin_client.get("/injuries/player/2/history")

    assert "复诊跟踪记录已保存" in response.get_data(as_text=True)
    assert INJURY_FOLLOWUPS[-1]["pain_score"] == 2
    assert "复诊跟踪" in history.get_data(as_text=True)


def test_bad_query_condition_keeps_page_available(admin_client):
    response = admin_client.get(
        "/injuries/?date_from=2026-08-01&date_to=2026-07-01&severity=bad"
    )
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "开始日期不能晚于结束日期" in text
    assert "伤病程度筛选条件非法" in text
