from pymysql.err import OperationalError

from app import app
from tests.helpers import csrf_data


def login(client):
    return client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )


def test_admin_can_assign_player_to_coach_when_database_is_unavailable(monkeypatch):
    import app as app_module
    import coaches.routes as coach_routes

    monkeypatch.setattr(
        coach_routes,
        "FALLBACK_COACHES",
        [{"id": 1, "name": "Coach A"}, {"id": 2, "name": "Coach B"}],
    )
    monkeypatch.setattr(
        app_module,
        "PLAYERS",
        [{"id": 10, "name": "Athlete", "coach_id": 1}],
    )
    monkeypatch.setattr(coach_routes, "fetch_one", lambda *args, **kwargs: (_ for _ in ()).throw(OperationalError(2003, "offline")))

    client = app.test_client()
    login(client)
    response = client.post(
        "/coaches/2/assign-players",
        data=csrf_data(client, {"player_ids": "10"}),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert app_module.PLAYERS[0]["coach_id"] == 2
