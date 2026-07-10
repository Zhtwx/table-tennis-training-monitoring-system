from app import app


def login(client, username="admin", password="admin123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def test_coach_list_page_renders(monkeypatch):
    import coaches.routes as coach_routes

    monkeypatch.setattr(
        coach_routes,
        "fetch_all",
        lambda query, params=None: [
            {
                "id": 1,
                "name": "陈指导",
                "gender": "男",
                "phone": "13800000001",
                "email": "chen@example.com",
                "specialty": "发接发训练",
                "hire_date": "2026-07-01",
                "player_count": 2,
                "latest_training_date": "2026-07-08",
            }
        ],
    )

    client = app.test_client()
    login(client)

    response = client.get("/coaches/")

    assert response.status_code == 200
    assert "陈指导" in response.get_data(as_text=True)


def test_coach_form_page_renders():
    client = app.test_client()
    login(client)

    response = client.get("/coaches/add")

    assert response.status_code == 200
    assert "教练员" in response.get_data(as_text=True)


def test_coach_players_page_renders(monkeypatch):
    import coaches.routes as coach_routes

    monkeypatch.setattr(
        coach_routes,
        "fetch_one",
        lambda query, params=None: {"id": 1, "name": "陈指导"},
    )
    monkeypatch.setattr(
        coach_routes,
        "fetch_all",
        lambda query, params=None: [
            {
                "id": 1,
                "name": "王一鸣",
                "gender": "男",
                "birth_date": "2007-03-10",
                "team": "一队",
                "skill_level": "一级运动员",
                "latest_training_date": "2026-07-08",
            }
        ],
    )

    client = app.test_client()
    login(client)

    response = client.get("/coaches/1/players")

    assert response.status_code == 200
    assert "王一鸣" in response.get_data(as_text=True)
