from app import app


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

    assert response.status_code == 200
    assert "训练强度结构" in body
    assert "体能能力雷达" in body
    assert "trainingLoadStackChart" in body
    assert "fitnessRadarChart" in body
    assert "dashboardData" in body
    assert "165分钟" in body
    assert "1,260h" not in body
