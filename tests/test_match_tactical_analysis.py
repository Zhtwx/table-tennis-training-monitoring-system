from copy import deepcopy

import pytest

import app as app_module
from app import app
from tests.helpers import csrf_data


def login(client, username="admin", password="admin123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def test_three_phase_stat_calculation_handles_zero_denominator_without_level():
    result = app_module.calculate_three_phase_stats(
        [
            {"phase_code": "serve_attack", "points_won": 4, "points_lost": 2},
            {"phase_code": "receive_attack", "points_won": 0, "points_lost": 0},
            {"phase_code": "rally", "points_won": 3, "points_lost": 1},
        ],
        standard_verified=False,
    )

    receive_attack = next(item for item in result if item["phase_code"] == "receive_attack")
    serve_attack = next(item for item in result if item["phase_code"] == "serve_attack")

    assert serve_attack["scoring_rate"] == pytest.approx(66.67)
    assert serve_attack["usage_rate"] == pytest.approx(60.0)
    assert serve_attack["evaluation_level"] is None
    assert receive_attack["scoring_rate"] is None
    assert receive_attack["usage_rate"] is None
    assert receive_attack["display_note"] == "无该段数据"


def test_three_phase_stat_calculation_rejects_negative_points():
    with pytest.raises(app_module.ValidationError, match="非负整数"):
        app_module.calculate_three_phase_stats(
            [{"phase_code": "serve_attack", "points_won": -1, "points_lost": 0}],
            standard_verified=False,
        )


def test_match_analysis_form_saves_unverified_three_phase_analysis():
    original_analyses = deepcopy(app_module.MATCH_TACTICAL_ANALYSES)
    original_phase_stats = deepcopy(app_module.MATCH_PHASE_STATS)
    original_analysis_counter = app_module.MATCH_ANALYSIS_ID_COUNTER
    original_phase_counter = app_module.MATCH_PHASE_STAT_ID_COUNTER
    try:
        client = app.test_client()
        login(client)
        match = app_module.MATCH_RESULTS[0]

        response = client.post(
            f"/matches/{match['id']}/analysis",
            data=csrf_data(
                client,
                {
                    "analysis_method": "three_phase",
                    "status": "confirmed",
                    "coach_summary": "教练人工复盘结论",
                    "serve_attack_points_won": "4",
                    "serve_attack_points_lost": "2",
                    "receive_attack_points_won": "0",
                    "receive_attack_points_lost": "0",
                    "rally_points_won": "3",
                    "rally_points_lost": "1",
                },
            ),
            follow_redirects=True,
        )

        body = response.get_data(as_text=True)
        created = app_module.MATCH_TACTICAL_ANALYSES[-1]
        created_stats = [
            item for item in app_module.MATCH_PHASE_STATS if item["analysis_id"] == created["id"]
        ]

        assert response.status_code == 200
        assert created["match_id"] == match["id"]
        assert created["version_no"] == 1
        assert created["status"] == "confirmed"
        assert len(created_stats) == 3
        assert all(item["evaluation_level"] is None for item in created_stats)
        assert "标准待核验" in body
        assert "无该段数据" in body
        assert "教练人工复盘结论" in body
    finally:
        app_module.MATCH_TACTICAL_ANALYSES[:] = original_analyses
        app_module.MATCH_PHASE_STATS[:] = original_phase_stats
        app_module.MATCH_ANALYSIS_ID_COUNTER = original_analysis_counter
        app_module.MATCH_PHASE_STAT_ID_COUNTER = original_phase_counter
