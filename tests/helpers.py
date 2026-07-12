def csrf_token(client):
    with client.session_transaction() as session:
        token = session.get("_csrf_token")
        if not token:
            token = "test-csrf-token"
            session["_csrf_token"] = token
        return token


def csrf_data(client, data=None):
    payload = dict(data or {})
    payload["csrf_token"] = csrf_token(client)
    return payload
