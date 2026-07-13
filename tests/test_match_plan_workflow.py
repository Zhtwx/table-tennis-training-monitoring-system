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


def test_match_list_provides_link_to_create_training_plan():
    client = app.test_client()
    login(client)

    response = client.get("/matches/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "制定训练计划" in body
    assert "source_type=match" in body


def test_training_plan_form_shows_match_source_context():
    client = app.test_client()
    login(client)

    match = app_module.MATCH_RESULTS[0]
    response = client.get(f"/training/plans?source_type=match&source_match_id={match['id']}")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "来源比赛" in body
    assert match["match_name"] in body
    assert str(match["athlete_id"]) in body


def test_training_plan_created_from_match_keeps_source_reference():
    original_plans = deepcopy(app_module.TRAINING_PLANS)
    original_counter = app_module.PLAN_ID_COUNTER
    original_items = deepcopy(app_module.TRAINING_PLAN_ITEMS)
    original_item_counter = app_module.PLAN_ITEM_ID_COUNTER
    try:
        client = app.test_client()
        login(client)

        match = app_module.MATCH_RESULTS[0]
        response = client.post(
            "/training/plans",
            data=csrf_data(
                client,
                {
                    "athlete_id": str(match["athlete_id"]),
                    "coach_id": "1",
                    "plan_datetime": "2026-07-20T09:00",
                    "content": "根据比赛结果安排后续训练重点",
                    "intensity": "中",
                    "duration": "60",
                    "location": "训练馆A",
                    "source_type": "match",
                    "source_match_id": str(match["id"]),
                    "source_summary": match["match_name"],
                    "item_module_type": ["technique_tactic"],
                    "item_title": ["根据比赛复盘制定技战术项目"],
                    "item_target_description": ["由教练人工确认比赛问题和训练目标"],
                    "item_planned_sessions": ["3"],
                    "item_planned_minutes": ["45"],
                    "item_intensity": ["中"],
                },
            ),
            follow_redirects=True,
        )

        created = app_module.TRAINING_PLANS[-1]
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert created.get("source_type") == "match"
        assert created.get("source_match_id") == match["id"]
        assert created.get("source_summary") == match["match_name"]
        assert "来源比赛" in body
        assert match["match_name"] in body
    finally:
        app_module.TRAINING_PLANS[:] = original_plans
        app_module.PLAN_ID_COUNTER = original_counter
        app_module.TRAINING_PLAN_ITEMS[:] = original_items
        app_module.PLAN_ITEM_ID_COUNTER = original_item_counter


def test_confirmed_match_analysis_is_preferred_when_creating_training_plan():
    original_plans = deepcopy(app_module.TRAINING_PLANS)
    original_counter = app_module.PLAN_ID_COUNTER
    original_items = deepcopy(app_module.TRAINING_PLAN_ITEMS)
    original_item_counter = app_module.PLAN_ITEM_ID_COUNTER
    original_analyses = deepcopy(app_module.MATCH_TACTICAL_ANALYSES)
    original_phase_stats = deepcopy(app_module.MATCH_PHASE_STATS)
    original_analysis_counter = app_module.MATCH_ANALYSIS_ID_COUNTER
    original_phase_counter = app_module.MATCH_PHASE_STAT_ID_COUNTER
    try:
        client = app.test_client()
        login(client)

        match = app_module.MATCH_RESULTS[0]
        analysis = app_module.save_match_tactical_analysis(
            match["id"],
            {
                "analysis_method": "three_phase",
                "status": "confirmed",
                "coach_summary": "已确认分析：接抢段衔接由教练人工标记为后续观察重点",
                "serve_attack_points_won": "4",
                "serve_attack_points_lost": "2",
                "receive_attack_points_won": "1",
                "receive_attack_points_lost": "3",
                "rally_points_won": "3",
                "rally_points_lost": "2",
            },
            "admin",
        )

        response = client.get(f"/training/plans?source_type=match&source_match_id={match['id']}")
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "已确认技战术分析版本：V1" in body
        assert "标准待核验" in body
        assert "已确认分析：接抢段衔接由教练人工标记为后续观察重点" in body
        assert f'name="source_analysis_id" value="{analysis["id"]}"' in body
        assert 'name="source_type" value="match_analysis"' in body

        response = client.post(
            "/training/plans",
            data=csrf_data(
                client,
                {
                    "athlete_id": str(match["athlete_id"]),
                    "coach_id": "1",
                    "plan_datetime": "2026-07-21T09:00",
                    "content": "根据已确认技战术分析安排训练计划",
                    "intensity": "中",
                    "duration": "60",
                    "location": "训练馆A",
                    "source_type": "match_analysis",
                    "source_match_id": str(match["id"]),
                    "source_analysis_id": str(analysis["id"]),
                    "source_summary": "",
                    "item_module_type": ["technique_tactic"],
                    "item_title": ["接抢衔接人工训练项目"],
                    "item_target_description": ["由教练依据已确认分析人工制定"],
                    "item_planned_sessions": ["3"],
                    "item_planned_minutes": ["45"],
                    "item_intensity": ["中"],
                },
            ),
            follow_redirects=True,
        )

        created = app_module.TRAINING_PLANS[-1]

        assert response.status_code == 200
        assert created.get("source_type") == "match_analysis"
        assert created.get("source_match_id") == match["id"]
        assert created.get("source_analysis_id") == analysis["id"]
        assert "已确认技战术分析 V1" in created.get("source_summary")
        assert "接抢段衔接" in created.get("source_summary")
    finally:
        app_module.TRAINING_PLANS[:] = original_plans
        app_module.PLAN_ID_COUNTER = original_counter
        app_module.TRAINING_PLAN_ITEMS[:] = original_items
        app_module.PLAN_ITEM_ID_COUNTER = original_item_counter
        app_module.MATCH_TACTICAL_ANALYSES[:] = original_analyses
        app_module.MATCH_PHASE_STATS[:] = original_phase_stats
        app_module.MATCH_ANALYSIS_ID_COUNTER = original_analysis_counter
        app_module.MATCH_PHASE_STAT_ID_COUNTER = original_phase_counter


def test_draft_match_analysis_is_not_used_as_training_plan_source():
    original_analyses = deepcopy(app_module.MATCH_TACTICAL_ANALYSES)
    original_phase_stats = deepcopy(app_module.MATCH_PHASE_STATS)
    original_analysis_counter = app_module.MATCH_ANALYSIS_ID_COUNTER
    original_phase_counter = app_module.MATCH_PHASE_STAT_ID_COUNTER
    try:
        client = app.test_client()
        login(client)

        match = app_module.MATCH_RESULTS[0]
        app_module.save_match_tactical_analysis(
            match["id"],
            {
                "analysis_method": "three_phase",
                "status": "draft",
                "coach_summary": "草稿分析不能作为普通改进计划依据",
                "serve_attack_points_won": "4",
                "serve_attack_points_lost": "2",
                "receive_attack_points_won": "1",
                "receive_attack_points_lost": "3",
                "rally_points_won": "3",
                "rally_points_lost": "2",
            },
            "admin",
        )

        response = client.get(f"/training/plans?source_type=match&source_match_id={match['id']}")
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "暂无已确认技战术分析，仅可作为比赛结果来源；需先完成分析确认后再作为普通改进计划依据。" in body
        assert 'name="source_type" value="match"' in body
        assert 'name="source_analysis_id"' not in body
        assert "草稿分析不能作为普通改进计划依据" not in body
    finally:
        app_module.MATCH_TACTICAL_ANALYSES[:] = original_analyses
        app_module.MATCH_PHASE_STATS[:] = original_phase_stats
        app_module.MATCH_ANALYSIS_ID_COUNTER = original_analysis_counter
        app_module.MATCH_PHASE_STAT_ID_COUNTER = original_phase_counter
