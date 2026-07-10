import db


def test_mysql_connection_uses_short_timeout_by_default(monkeypatch):
    captured = {}

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.delenv("DB_CONNECT_TIMEOUT", raising=False)
    monkeypatch.setattr(db.pymysql, "connect", fake_connect)

    db.get_mysql_connection()

    assert captured["connect_timeout"] == 1


def test_mysql_connection_timeout_can_be_configured(monkeypatch):
    captured = {}

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setenv("DB_CONNECT_TIMEOUT", "3")
    monkeypatch.setattr(db.pymysql, "connect", fake_connect)

    db.get_mysql_connection()

    assert captured["connect_timeout"] == 3
