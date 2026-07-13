from app import app


def login(client, username="admin", password="admin123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def test_coach_list_falls_back_to_sample_data_when_database_unavailable(monkeypatch):
    import coaches.routes as coach_routes
    from pymysql.err import OperationalError

    def unavailable(*args, **kwargs):
        raise OperationalError(2003, "Can't connect to MySQL server on 'localhost'")

    monkeypatch.setattr(coach_routes, "fetch_all", unavailable)

    client = app.test_client()
    login(client)

    response = client.get("/coaches/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "\u5f20\u6559\u7ec3" in body
    assert "\u6559\u7ec3\u5458\u6570\u636e\u6682\u65f6\u4e0d\u53ef\u7528" not in body


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


def test_coach_list_supports_screening(monkeypatch):
    import coaches.routes as coach_routes

    sample_rows = [
        {
            "id": 1,
            "name": "张教练",
            "gender": "男",
            "phone": "13800000001",
            "email": "zhang@example.com",
            "specialty": "乒乓球专项训练",
            "hire_date": "2026-07-01",
            "player_count": 2,
            "latest_training_date": "2026-07-08",
        },
        {
            "id": 2,
            "name": "李教练",
            "gender": "女",
            "phone": "13800000002",
            "email": "li@example.com",
            "specialty": "体能训练与康复",
            "hire_date": "2026-07-02",
            "player_count": 0,
            "latest_training_date": None,
        },
    ]

    monkeypatch.setattr(coach_routes, "fetch_all", lambda query, params=None: sample_rows)

    client = app.test_client()
    login(client)

    response = client.get("/coaches/?keyword=张&has_players=yes")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "张教练" in body
    assert "李教练" not in body
    assert "当前命中 1 条" in body
    assert "启用 2 个查询条件" in body


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


def test_coach_players_page_supports_screening(monkeypatch):
    import coaches.routes as coach_routes

    monkeypatch.setattr(
        coach_routes,
        "fetch_one",
        lambda query, params=None: {"id": 1, "name": "张教练"},
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
            },
            {
                "id": 2,
                "name": "李清扬",
                "gender": "女",
                "birth_date": "2008-05-21",
                "team": "二队",
                "skill_level": "二级运动员",
                "latest_training_date": "2026-07-04",
            },
        ],
    )

    client = app.test_client()
    login(client)

    response = client.get("/coaches/1/players?keyword=王&team=一队&skill_level=一级运动员")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "王一鸣" in body
    assert "李清扬" not in body
    assert "当前命中 1 条" in body
    assert "启用 3 个查询条件" in body
