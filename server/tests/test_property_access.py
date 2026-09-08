from tests.conftest import auth_headers


def _create_property(client, token, **overrides):
    payload = {"deal_type": "sale", "city": "تهران", "address": "آدرس تست", "details": {"price": 1000000000}}
    payload.update(overrides)
    resp = client.post("/properties/", json=payload, headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_agent_sees_only_own_properties(client, agent_token, agent2_token):
    _create_property(client, agent_token, address="فایل مشاور یک")
    _create_property(client, agent2_token, address="فایل مشاور دو")

    resp = client.get("/properties/", headers=auth_headers(agent_token))
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["address"] == "فایل مشاور یک"

    resp2 = client.get("/properties/", headers=auth_headers(agent2_token))
    data2 = resp2.json()
    assert data2["total"] == 1
    assert data2["items"][0]["address"] == "فایل مشاور دو"


def test_admin_sees_all_properties(client, agent_token, agent2_token, admin_token):
    _create_property(client, agent_token, address="فایل مشاور یک")
    _create_property(client, agent2_token, address="فایل مشاور دو")

    resp = client.get("/properties/", headers=auth_headers(admin_token))
    data = resp.json()
    assert data["total"] == 2


def test_agent_cannot_edit_other_agents_property(client, agent_token, agent2_token):
    prop = _create_property(client, agent_token)
    resp = client.put(
        f"/properties/{prop['id']}",
        json={**prop, "address": "دستکاری شده"},
        headers=auth_headers(agent2_token),
    )
    assert resp.status_code == 404  # نه ۴۰۳؛ عمداً طوری طراحی شده که وجودش را هم فاش نکند


def test_agent_cannot_deactivate_other_agents_property(client, agent_token, agent2_token):
    prop = _create_property(client, agent_token)
    resp = client.delete(f"/properties/{prop['id']}", headers=auth_headers(agent2_token))
    assert resp.status_code == 404


def test_admin_can_edit_agents_property(client, agent_token, admin_token):
    prop = _create_property(client, agent_token)
    resp = client.put(
        f"/properties/{prop['id']}",
        json={**prop, "address": "ویرایش‌شده توسط مدیر"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["address"] == "ویرایش‌شده توسط مدیر"


def test_new_property_owner_is_creator(client, agent_token, agent_user):
    prop = _create_property(client, agent_token)
    assert prop["owner_agent_id"] == agent_user.id


def test_deactivate_then_archive_then_reactivate(client, agent_token):
    prop = _create_property(client, agent_token)

    # فعال -> غیرفعال
    resp = client.delete(f"/properties/{prop['id']}", headers=auth_headers(agent_token))
    assert resp.status_code == 200

    active_list = client.get("/properties/", headers=auth_headers(agent_token)).json()
    assert active_list["total"] == 0

    archived_list = client.get("/properties/archived", headers=auth_headers(agent_token)).json()
    assert archived_list["total"] == 1

    # بازگردانی
    resp = client.post(f"/properties/{prop['id']}/reactivate", headers=auth_headers(agent_token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"

    active_list_after = client.get("/properties/", headers=auth_headers(agent_token)).json()
    assert active_list_after["total"] == 1
