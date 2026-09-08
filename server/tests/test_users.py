from tests.conftest import auth_headers


def test_agent_cannot_access_user_management(client, agent_token):
    resp = client.get("/users/", headers=auth_headers(agent_token))
    assert resp.status_code == 403


def test_admin_can_create_agent(client, admin_token):
    resp = client.post(
        "/users/",
        json={"username": "new_agent", "full_name": "مشاور جدید", "password": "pass123456", "role": "agent"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "agent"


def test_cannot_create_duplicate_username(client, admin_token, agent_user):
    resp = client.post(
        "/users/",
        json={"username": "test_agent1", "full_name": "تکراری", "password": "pass123456", "role": "agent"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400


def test_deactivate_invalidates_existing_token(client, admin_token, agent_token, agent_user):
    # قبل از غیرفعال‌سازی، توکن مشاور باید کار کند
    resp = client.get("/properties/", headers=auth_headers(agent_token))
    assert resp.status_code == 200

    # مدیر حساب مشاور را غیرفعال می‌کند
    resp = client.post(f"/users/{agent_user.id}/deactivate", headers=auth_headers(admin_token))
    assert resp.status_code == 200

    # همان توکن قدیمی مشاور دیگر نباید کار کند
    resp = client.get("/properties/", headers=auth_headers(agent_token))
    assert resp.status_code == 401


def test_reset_password_invalidates_existing_token(client, admin_token, agent_token, agent_user):
    resp = client.post(
        f"/users/{agent_user.id}/reset-password",
        json={"new_password": "brandnewpass123"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200

    # توکن قدیمی باید باطل شده باشد
    resp = client.get("/properties/", headers=auth_headers(agent_token))
    assert resp.status_code == 401

    # ورود با رمز جدید باید کار کند
    resp = client.post("/auth/login", data={"username": "test_agent1", "password": "brandnewpass123"})
    assert resp.status_code == 200


def test_admin_can_update_agent_phone(client, admin_token, agent_user):
    resp = client.put(
        f"/users/{agent_user.id}/phone",
        json={"phone": "09121234567"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["phone"] == "09121234567"

    # فهرست کاربران هم باید همین شماره را نشان دهد
    users = client.get("/users/", headers=auth_headers(admin_token)).json()
    updated = [u for u in users if u["id"] == agent_user.id][0]
    assert updated["phone"] == "09121234567"


def test_agent_cannot_update_phone(client, agent_token, agent_user):
    resp = client.put(
        f"/users/{agent_user.id}/phone",
        json={"phone": "09121234567"},
        headers=auth_headers(agent_token),
    )
    assert resp.status_code == 403
