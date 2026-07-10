from app import app


def login(client, username="admin", password="admin123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def test_rehab_page_renders_tracking_ledger_and_risk_filter():
    client = app.test_client()
    login(client)

    response = client.get("/rehab/?risk_level=high")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "康复跟踪明细" in body
    assert "复训建议" in body
    assert "赵若溪" in body
    assert "王一鸣" not in body


def test_match_page_renders_statistics_and_result_filter():
    client = app.test_client()
    login(client)

    response = client.get("/matches/?result=负")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "比赛成绩统计" in body
    assert "胜率" in body
    assert "陈昊然" in body
    assert "王一鸣" in body


def test_auth_page_renders_permission_matrix_and_database_accounts():
    client = app.test_client()
    login(client)

    response = client.get("/auth/users")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "权限矩阵" in body
    assert "coach_app" in body
    assert "训练数据录入" in body


def test_coach_cannot_open_permission_management():
    client = app.test_client()
    login(client, "coach", "user123")

    response = client.get("/auth/users")

    assert response.status_code == 403


def test_settings_page_renders_dictionary_and_database_health_checks():
    client = app.test_client()
    login(client)

    response = client.get("/settings/dictionary")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "系统运行检查" in body
    assert "pingpang_db" in body
    assert "视图" in body
    assert "存储过程" in body
