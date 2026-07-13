from app import (
    ADDITIONAL_ATHLETE_COUNT,
    ADDITIONAL_DEMO_RECORD_COUNT,
    COACHES,
    DEMO_EXTENSION_RECORD_COUNT,
    FITNESS_TESTS,
    FOOTWORK_TRAINING_RECORDS,
    INJURY_RECORDS,
    MATCH_RESULTS,
    PLAYERS,
    TECHNIQUE_TACTIC_TRAINING_RECORDS,
    TRAINING_PLANS,
    app,
    build_home_dashboard_data,
)


def login(client, username="admin", password="admin123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def test_home_dashboard_renders_training_load_and_fitness_structure_charts():
    client = app.test_client()
    login(client)

    response = client.get("/")
    body = response.get_data(as_text=True)
    dashboard = build_home_dashboard_data()

    assert response.status_code == 200
    assert "训练强度结构" in body
    assert "体能能力雷达" in body
    assert "trainingLoadStackChart" in body
    assert "fitnessRadarChart" in body
    assert "dashboardData" in body
    assert f"{dashboard['cards']['current_month_duration']}分钟" in body
    assert "1,260h" not in body


def test_home_dashboard_charts_have_at_least_10_data_points():
    dashboard = build_home_dashboard_data()

    assert len(dashboard["month_labels"]) >= 10
    assert len(dashboard["monthly_duration"]) == len(dashboard["month_labels"])
    assert len(dashboard["intensity_month_labels"]) >= 10
    assert all(len(series["data"]) == len(dashboard["intensity_month_labels"]) for series in dashboard["intensity_series"])
    assert len(dashboard["fitness_radar_indicators"]) >= 10
    assert len(dashboard["fitness_radar_values"]) == len(dashboard["fitness_radar_indicators"])
    assert len(dashboard["fitness_target_values"]) == len(dashboard["fitness_radar_indicators"])


def test_demo_seed_data_adds_22_more_athletes_and_syncs_dashboard_stats():
    expected_seed_count = (
        (len(PLAYERS) - 4)
        + (len(TRAINING_PLANS) - 2)
        + len(FOOTWORK_TRAINING_RECORDS)
        + len(TECHNIQUE_TACTIC_TRAINING_RECORDS)
        + (len(FITNESS_TESTS) - 4)
        + (len(INJURY_RECORDS) - 4)
        + (len(MATCH_RESULTS) - 5)
    )
    player_ids = {player["id"] for player in PLAYERS}
    coach_ids = {coach["id"] for coach in COACHES}
    dashboard = build_home_dashboard_data()
    all_training_records = FOOTWORK_TRAINING_RECORDS + TECHNIQUE_TACTIC_TRAINING_RECORDS

    assert DEMO_EXTENSION_RECORD_COUNT == 22
    assert ADDITIONAL_ATHLETE_COUNT == 22
    assert expected_seed_count == DEMO_EXTENSION_RECORD_COUNT + ADDITIONAL_DEMO_RECORD_COUNT
    assert len(PLAYERS) == 30
    assert len(TRAINING_PLANS) == 30
    assert len(FOOTWORK_TRAINING_RECORDS) == 14
    assert len(TECHNIQUE_TACTIC_TRAINING_RECORDS) == 14
    assert len(FITNESS_TESTS) == 29
    assert len(INJURY_RECORDS) == 14
    assert len(MATCH_RESULTS) == 17

    assert {plan["athlete_id"] for plan in TRAINING_PLANS} <= player_ids
    assert {record["athlete_id"] for record in all_training_records} <= player_ids
    assert {test["athlete_id"] for test in FITNESS_TESTS} <= player_ids
    assert {record["athlete_id"] for record in INJURY_RECORDS} <= player_ids
    assert {match["athlete_id"] for match in MATCH_RESULTS} <= player_ids
    assert {plan["coach_id"] for plan in TRAINING_PLANS} <= coach_ids
    assert {test["tester_id"] for test in FITNESS_TESTS} <= coach_ids
    assert all(
        any(plan["athlete_id"] == player["id"] for plan in TRAINING_PLANS)
        and any(record["athlete_id"] == player["id"] for record in all_training_records)
        and any(test["athlete_id"] == player["id"] for test in FITNESS_TESTS)
        for player in PLAYERS
        if player["id"] >= 9
    )

    expected_month_duration = sum(
        plan["duration"] for plan in TRAINING_PLANS if plan["plan_datetime"].startswith("2026-07")
    )
    expected_active_injuries = sum(
        1 for record in INJURY_RECORDS if record["recovery_status"] in {"治疗中", "康复中"}
    )

    assert dashboard["cards"]["total_athletes"] == 30
    assert dashboard["cards"]["training_plan_count"] == 30
    assert dashboard["cards"]["current_month_duration"] == expected_month_duration
    assert dashboard["cards"]["active_injuries"] == expected_active_injuries
    assert "2026-07" in dashboard["intensity_month_labels"]
    assert sum(dashboard["intensity_series"][2]["data"]) > 0
