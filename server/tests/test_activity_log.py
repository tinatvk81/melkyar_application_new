from tests.conftest import auth_headers


def test_agent_cannot_view_activity_log(client, agent_token):
    resp = client.get("/activity-logs/", headers=auth_headers(agent_token))
    assert resp.status_code == 403


def test_login_and_property_actions_are_logged(client, agent_token, admin_token):
    prop = client.post(
        "/properties/",
        json={"deal_type": "sale", "city": "تهران", "address": "تست لاگ", "details": {"price": 1000000000}},
        headers=auth_headers(agent_token),
    ).json()

    client.delete(f"/properties/{prop['id']}", headers=auth_headers(agent_token))
    client.post(f"/properties/{prop['id']}/reactivate", headers=auth_headers(agent_token))

    resp = client.get("/activity-logs/", params={"days": 0}, headers=auth_headers(admin_token))
    assert resp.status_code == 200
    actions = [log["action"] for log in resp.json()["items"]]

    assert "login" in actions
    assert "create" in actions
    assert "deactivate" in actions
    assert "reactivate" in actions


def test_activity_log_filter_by_entity_type(client, agent_token, admin_token):
    client.post(
        "/properties/",
        json={"deal_type": "sale", "city": "تهران", "details": {"price": 1000000000}},
        headers=auth_headers(agent_token),
    )
    resp = client.get("/activity-logs/", params={"entity_type": "property", "days": 0}, headers=auth_headers(admin_token))
    data = resp.json()
    assert all(log["entity_type"] == "property" for log in data["items"])
    assert data["total"] >= 1
