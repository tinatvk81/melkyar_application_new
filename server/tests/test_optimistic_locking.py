from tests.conftest import auth_headers


def _create_property(client, token, **overrides):
    payload = {"deal_type": "sale", "city": "تهران", "address": "آدرس تست", "details": {"price": 1000000000}}
    payload.update(overrides)
    resp = client.post("/properties/", json=payload, headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_new_property_starts_at_version_1(client, agent_token):
    prop = _create_property(client, agent_token)
    assert prop["version"] == 1


def test_successful_update_increments_version(client, agent_token):
    prop = _create_property(client, agent_token)
    resp = client.put(
        f"/properties/{prop['id']}",
        json={**prop, "address": "ویرایش اول", "version": prop["version"]},
        headers=auth_headers(agent_token),
    )
    assert resp.status_code == 200
    assert resp.json()["version"] == 2


def test_stale_version_update_is_rejected(client, agent_token):
    """
    شبیه‌سازی دو کاربر هم‌زمان: هردو نسخه‌ی ۱ را می‌خوانند، اولی ذخیره می‌کند
    (نسخه می‌شود ۲)، دومی با نسخه‌ی قدیمی (۱) سعی می‌کند ذخیره کند — باید رد شود.
    """
    prop = _create_property(client, agent_token)
    original_version = prop["version"]

    # کاربر «اول» با موفقیت ذخیره می‌کند
    resp_a = client.put(
        f"/properties/{prop['id']}",
        json={**prop, "address": "ذخیره‌شده توسط کاربر اول", "version": original_version},
        headers=auth_headers(agent_token),
    )
    assert resp_a.status_code == 200

    # کاربر «دوم» با همان نسخه‌ی قدیمی (که قبل از تغییر کاربر اول خوانده بود) سعی می‌کند
    resp_b = client.put(
        f"/properties/{prop['id']}",
        json={**prop, "address": "نباید ذخیره شود", "version": original_version},
        headers=auth_headers(agent_token),
    )
    assert resp_b.status_code == 409

    # بررسی این‌که داده‌ی نهایی همان چیزی است که کاربر اول ذخیره کرده
    final = client.get("/properties/", headers=auth_headers(agent_token)).json()["items"][0]
    assert final["address"] == "ذخیره‌شده توسط کاربر اول"
    assert final["version"] == 2
