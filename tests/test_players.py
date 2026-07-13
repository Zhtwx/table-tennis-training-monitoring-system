from copy import deepcopy

from app import COACHES, PLAYERS, app
from tests.helpers import csrf_data


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
        "coach_id": "1",
    }
    data.update(overrides)
    return data


def test_seed_players_have_primary_coach_fields():
    coach_names = {coach["id"]: coach["name"] for coach in COACHES}

    assert PLAYERS
    for player in PLAYERS:
        assert player.get("coach_id") in coach_names
        assert player.get("coach_name") == coach_names[player["coach_id"]]


def test_admin_can_create_view_edit_delete_player_and_filter():
    original_players = deepcopy(PLAYERS)
    try:
        client = app.test_client()
        login(client)

        create_response = client.post(
            "/players/create",
            data=csrf_data(client, player_payload()),
            follow_redirects=True,
        )

        assert create_response.status_code == 200
        assert len(PLAYERS) == len(original_players) + 1
        created = PLAYERS[-1]
        assert created["student_no"] == "2026999"
        assert created["name"] == "测试队员"
        assert created["coach_id"] == 1
        assert created["coach_name"] == "张教练"

        detail_response = client.get(f"/players/{created['id']}")
        detail_body = detail_response.get_data(as_text=True)

        assert detail_response.status_code == 200
        assert "测试队员" in detail_body
        assert "右手横板快攻" in detail_body
        assert "主教练" in detail_body
        assert "张教练" in detail_body

        filter_response = client.get(
            "/players/?student_no=2026999&name=测试&gender=男"
            "&level=first&play_style=横板&injury_status=healthy"
            "&age_min=17&age_max=19&coach_id=1"
        )
        filter_body = filter_response.get_data(as_text=True)

        assert filter_response.status_code == 200
        assert "测试队员" in filter_body

        edit_response = client.post(
            f"/players/{created['id']}/edit",
            data=csrf_data(
                client,
                player_payload(name="测试队员改", age="19", level_code="second", coach_id="2"),
            ),
            follow_redirects=True,
        )

        assert edit_response.status_code == 200
        assert PLAYERS[-1]["name"] == "测试队员改"
        assert PLAYERS[-1]["age"] == 19
        assert PLAYERS[-1]["level_code"] == "second"
        assert PLAYERS[-1]["coach_id"] == 2
        assert PLAYERS[-1]["coach_name"] == "李教练"

        delete_response = client.post(
            f"/players/{created['id']}/delete",
            data=csrf_data(client),
            follow_redirects=True,
        )

        assert delete_response.status_code == 200
        assert all(player["id"] != created["id"] for player in PLAYERS)
    finally:
        PLAYERS[:] = original_players


def test_player_list_supports_pagination_with_filters():
    original_players = deepcopy(PLAYERS)
    try:
        PLAYERS[:] = []
        for index in range(12):
            PLAYERS.append(
                {
                    "id": index + 1,
                    "student_no": f"PX{index + 1:03d}",
                    "name": f"分页队员{index + 1:02d}",
                    "gender": "男",
                    "age": 18 + index,
                    "level": "一级运动员",
                    "skill_level": "一级运动员",
                    "level_code": "first",
                    "play_style": "右手横板快攻",
                    "grip": "右手横板",
                    "contact_phone": "13800000000",
                    "injury_status": "健康",
                    "injury_status_code": "healthy",
                    "coach_id": COACHES[0]["id"],
                    "coach_name": COACHES[0]["name"],
                }
            )

        client = app.test_client()
        login(client)
        response = client.get("/players/?gender=男&page=2")
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "分页队员11" in body
        assert "分页队员12" in body
        assert "分页队员01" not in body
        assert "第 2 / 2 页" in body
        assert "page=1" in body
        assert "gender=%E7%94%B7" in body or "gender=男" in body
    finally:
        PLAYERS[:] = original_players


def test_coach_cannot_open_player_create_page():
    client = app.test_client()
    login(client, "coach", "user123")

    response = client.get("/players/create")

    assert response.status_code == 403
