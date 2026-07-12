from copy import deepcopy

import app as app_module
from app import app
from tests.helpers import csrf_data


def login(client, username="admin", password="admin123", follow_redirects=True):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=follow_redirects,
    )


def test_login_rejects_external_next_redirect():
    client = app.test_client()

    response = client.post(
        "/login?next=http://evil.example/phishing",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_health_check_is_public():
    client = app.test_client()

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_training_plans_route_has_single_canonical_endpoint():
    matching_rules = [
        rule
        for rule in app.url_map.iter_rules()
        if rule.rule == "/training/plans"
    ]

    assert len(matching_rules) == 1
    assert matching_rules[0].endpoint == "training.plans"
    assert "POST" in matching_rules[0].methods


def test_legacy_training_record_url_redirects_to_canonical_records_url():
    client = app.test_client()
    login(client)

    response = client.get("/training/training_record", follow_redirects=False)

    assert response.status_code == 301
    assert response.headers["Location"] == "/training/records"


def test_coach_cannot_open_coach_write_pages():
    client = app.test_client()
    login(client, "coach", "user123")

    add_response = client.get("/coaches/add")
    edit_response = client.get("/coaches/edit/1")

    assert add_response.status_code == 403
    assert edit_response.status_code == 403


def test_coach_can_only_delete_owned_training_plan():
    original_plans = deepcopy(app_module.TRAINING_PLANS)
    original_audit_logs = deepcopy(getattr(app_module, "AUDIT_LOGS", []))
    try:
        client = app.test_client()
        login(client, "coach", "user123")

        other_plan_response = client.post(
            "/training/plans/1/delete",
            data=csrf_data(client),
            follow_redirects=True,
        )
        own_plan_response = client.post(
            "/training/plans/2/delete",
            data=csrf_data(client),
            follow_redirects=True,
        )

        assert other_plan_response.status_code == 403
        assert any(plan["id"] == 1 for plan in app_module.TRAINING_PLANS)
        assert own_plan_response.status_code == 200
        assert all(plan["id"] != 2 for plan in app_module.TRAINING_PLANS)
        assert app_module.AUDIT_LOGS[-1]["action"] == "delete"
        assert app_module.AUDIT_LOGS[-1]["target_type"] == "training_plan"
        assert app_module.AUDIT_LOGS[-1]["target_id"] == 2
        assert app_module.AUDIT_LOGS[-1]["username"] == "coach"
    finally:
        app_module.TRAINING_PLANS = original_plans
        if hasattr(app_module, "AUDIT_LOGS"):
            app_module.AUDIT_LOGS[:] = original_audit_logs


def test_missing_csrf_token_rejects_authenticated_write_request():
    original_plans = deepcopy(app_module.TRAINING_PLANS)
    try:
        client = app.test_client()
        login(client, "coach", "user123")

        response = client.post("/training/plans/2/delete", follow_redirects=False)

        assert response.status_code == 400
        assert any(plan["id"] == 2 for plan in app_module.TRAINING_PLANS)
    finally:
        app_module.TRAINING_PLANS = original_plans
