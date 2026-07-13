from app import app


def login(client, username="admin", password="admin123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def test_root_redirects_to_match_results_after_login():
    client = app.test_client()
    login(client)

    response = client.get("/", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "/matches/"


def test_navigation_groups_render_target_modules_without_dashboard():
    client = app.test_client()
    login(client)

    response = client.get("/matches/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "综合看板" not in body
    assert "训练业务" in body
    assert "人员与状态" in body
    assert "数据与管理" in body
    assert "运动员身体状态" in body
    assert "伤病记录" in body
    assert "康复跟踪" in body


def test_admin_users_page_exposes_system_maintenance_entry():
    client = app.test_client()
    login(client)

    response = client.get("/auth/users")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "系统维护" in body
    assert "/settings/dictionary" in body
