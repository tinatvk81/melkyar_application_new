from tests.conftest import auth_headers


def test_login_success(client, agent_user):
    resp = client.post("/auth/login", data={"username": "test_agent1", "password": "agentpass123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "agent"
    assert data["full_name"] == "مشاور یک"
    assert "access_token" in data


def test_login_wrong_password(client, agent_user):
    resp = client.post("/auth/login", data={"username": "test_agent1", "password": "wrong-password"})
    assert resp.status_code == 401


def test_login_nonexistent_user(client):
    resp = client.post("/auth/login", data={"username": "nobody", "password": "whatever"})
    assert resp.status_code == 401


def test_login_inactive_account_rejected(client, agent_user, db_session):
    agent_user.is_active = False
    db_session.commit()
    resp = client.post("/auth/login", data={"username": "test_agent1", "password": "agentpass123"})
    assert resp.status_code == 403


def test_protected_endpoint_requires_token(client):
    resp = client.get("/properties/")
    assert resp.status_code == 401


def test_protected_endpoint_rejects_garbage_token(client):
    resp = client.get("/properties/", headers=auth_headers("this-is-not-a-real-jwt"))
    assert resp.status_code == 401
