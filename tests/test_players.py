from copy import deepcopy

from app import PLAYERS, app


def login(client, username="admin", password="admin123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def player_payload(**overrides):
    data = {
        "student_no": "2026999",
        "name": "测试队员",
        "gender": "男",
        "age": "18",
        "level_code": "first",
        "play_style": "右手横板快攻",
        "grip": "右手横板",
        "contact_phone": "13800009999",
        "injury_status_code": "healthy",
    }
    data.update(overrides)
    return data


def test_admin_can_create_view_edit_delete_player_and_filter():
    original_players = deepcopy(PLAYERS)
    try:
        client = app.test_client()
        login(client)

        create_response = client.post(
            "/players/create",
            data=player_payload(),
            follow_redirects=True,
        )

        assert create_response.status_code == 200
        assert len(PLAYERS) == len(original_players) + 1
        created = PLAYERS[-1]
        assert created["student_no"] == "2026999"
        assert created["name"] == "测试队员"

        detail_response = client.get(f"/players/{created['id']}")
        detail_body = detail_response.get_data(as_text=True)

        assert detail_response.status_code == 200
        assert "测试队员" in detail_body
        assert "右手横板快攻" in detail_body

        filter_response = client.get(
            "/players/?student_no=2026999&name=测试&gender=男"
            "&level=first&play_style=横板&injury_status=healthy"
            "&age_min=17&age_max=19"
        )
        filter_body = filter_response.get_data(as_text=True)

        assert filter_response.status_code == 200
        assert "测试队员" in filter_body

        edit_response = client.post(
            f"/players/{created['id']}/edit",
            data=player_payload(name="测试队员改", age="19", level_code="second"),
            follow_redirects=True,
        )

        assert edit_response.status_code == 200
        assert PLAYERS[-1]["name"] == "测试队员改"
        assert PLAYERS[-1]["age"] == 19
        assert PLAYERS[-1]["level_code"] == "second"

        delete_response = client.post(
            f"/players/{created['id']}/delete",
            follow_redirects=True,
        )

        assert delete_response.status_code == 200
        assert all(player["id"] != created["id"] for player in PLAYERS)
    finally:
        PLAYERS[:] = original_players


def test_coach_cannot_open_player_create_page():
    client = app.test_client()
    login(client, "coach", "user123")

    response = client.get("/players/create")

    assert response.status_code == 403
