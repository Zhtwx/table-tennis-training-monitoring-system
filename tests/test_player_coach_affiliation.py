import pytest
from pathlib import Path

from app import ValidationError, validate_player_form


def valid_player_form(**overrides):
    form = {
        "student_no": "2026999",
        "name": "测试队员",
        "gender": "男",
        "age": "18",
        "level_code": "first",
        "play_style": "右手横板快攻",
        "grip": "右手横板",
        "contact_phone": "13800009999",
        "injury_status_code": "healthy",
        "coach_id": "1",
    }
    form.update(overrides)
    return form


def test_player_form_derives_coach_name_from_primary_coach_id():
    player = validate_player_form(valid_player_form(coach_id="1"))

    assert player["coach_id"] == 1
    assert player["coach_name"] == "张教练"


def test_player_form_rejects_unknown_primary_coach():
    with pytest.raises(ValidationError, match="所属教练不存在"):
        validate_player_form(valid_player_form(coach_id="999"))


def test_schema_enforces_and_initializes_primary_coach_affiliation():
    schema = Path("sql/pingpang_db.sql").read_text(encoding="utf-8")

    assert "primary_coach_id INT" in schema
    assert "FOREIGN KEY (primary_coach_id) REFERENCES coach(id)" in schema
    assert "ON DELETE RESTRICT ON UPDATE CASCADE" in schema
    assert "UPDATE athlete\nSET primary_coach_id = CASE id" in schema


def test_fallback_coach_membership_uses_primary_coach_not_training_plan(monkeypatch):
    import app as app_module
    import coaches.routes as coach_routes

    monkeypatch.setattr(coach_routes, "FALLBACK_COACHES", [{"id": 1}, {"id": 2}])
    monkeypatch.setattr(
        app_module,
        "PLAYERS",
        [{"id": 9, "name": "Athlete", "coach_id": 2}],
    )
    monkeypatch.setattr(
        coach_routes,
        "FALLBACK_TRAINING_PLANS",
        [{"athlete_id": 9, "coach_id": 1, "start_date": "2026-07-01"}],
    )

    counts = {row["id"]: row["player_count"] for row in coach_routes.fallback_coach_rows()}
    players = coach_routes.fallback_players_for_coach(2)

    assert counts == {1: 0, 2: 1}
    assert [player["id"] for player in players] == [9]


def test_fallback_coach_membership_uses_all_player_profiles():
    from app import PLAYERS
    import coaches.routes as coach_routes

    counts = {row["id"]: row["player_count"] for row in coach_routes.fallback_coach_rows()}
    coach_one_players = coach_routes.fallback_players_for_coach(1)

    assert sum(counts.values()) == len(PLAYERS)
    assert {player["id"] for player in coach_one_players} == {
        player["id"] for player in PLAYERS if player["coach_id"] == 1
    }


def test_coach_list_query_counts_primary_coach_assignments(monkeypatch):
    import coaches.routes as coach_routes
    from app import app

    queries = []

    def fetch_rows(query, params=None):
        queries.append(query)
        return []

    monkeypatch.setattr(coach_routes, "fetch_all", fetch_rows)

    client = app.test_client()
    client.post("/login", data={"username": "admin", "password": "admin123"})
    response = client.get("/coaches/")

    assert response.status_code == 200
    assert "LEFT JOIN athlete a ON c.id = a.primary_coach_id" in queries[0]


def test_coach_players_query_uses_primary_coach_assignments(monkeypatch):
    import coaches.routes as coach_routes
    from app import app

    queries = []

    monkeypatch.setattr(coach_routes, "fetch_one", lambda query, params=None: {"id": 1, "name": "Coach"})

    def fetch_rows(query, params=None):
        queries.append(query)
        return []

    monkeypatch.setattr(coach_routes, "fetch_all", fetch_rows)

    client = app.test_client()
    client.post("/login", data={"username": "admin", "password": "admin123"})
    response = client.get("/coaches/1/players")

    assert response.status_code == 200
    assert "WHERE a.primary_coach_id = %s" in queries[0]


def test_player_forms_render_primary_coach_selection():
    from app import app

    client = app.test_client()
    client.post("/login", data={"username": "admin", "password": "admin123"})

    create_response = client.get("/players/create")
    edit_response = client.get("/players/1/edit")

    for response in (create_response, edit_response):
        body = response.get_data(as_text=True)
        assert response.status_code == 200
        assert 'name="coach_id"' in body
        assert "张教练" in body
        assert "李教练" in body
