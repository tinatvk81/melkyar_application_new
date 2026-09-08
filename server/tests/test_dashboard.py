from datetime import date, timedelta

from tests.conftest import auth_headers


def _create_property(client, token, **overrides):
    payload = {"deal_type": "sale", "city": "تهران", "address": "آدرس تست", "details": {"price": 1000000000}}
    payload.update(overrides)
    resp = client.post("/properties/", json=payload, headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_dashboard_counts_by_deal_type(client, agent_token):
    _create_property(client, agent_token, deal_type="sale")
    _create_property(client, agent_token, deal_type="sale")
    _create_property(client, agent_token, deal_type="rent", details={"monthly_rent": 5000000})

    resp = client.get("/reports/dashboard", headers=auth_headers(agent_token))
    data = resp.json()
    assert data["total_active"] == 3
    assert data["by_deal_type"]["sale"] == 2
    assert data["by_deal_type"]["rent"] == 1


def test_dashboard_urgent_vs_upcoming_renewals(client, agent_token):
    today = date.today()
    _create_property(client, agent_token, deal_type="rent", details={"monthly_rent": 5000000},
                      contract_end_date=(today + timedelta(days=3)).isoformat())
    _create_property(client, agent_token, deal_type="rent", details={"monthly_rent": 5000000},
                      contract_end_date=(today + timedelta(days=20)).isoformat())
    _create_property(client, agent_token, deal_type="sale")  # بدون تاریخ پایان قرارداد

    resp = client.get("/reports/dashboard", headers=auth_headers(agent_token))
    data = resp.json()
    assert data["urgent_renewals"] == 1  # فقط زیر ۷ روز
    assert data["upcoming_renewals"] == 2  # هردو زیر ۳۰ روز


def test_dashboard_scoped_per_agent(client, agent_token, agent2_token):
    _create_property(client, agent_token)
    _create_property(client, agent2_token)
    _create_property(client, agent2_token)

    resp1 = client.get("/reports/dashboard", headers=auth_headers(agent_token))
    assert resp1.json()["total_active"] == 1

    resp2 = client.get("/reports/dashboard", headers=auth_headers(agent2_token))
    assert resp2.json()["total_active"] == 2


def test_dashboard_admin_sees_total_agents_and_activity(client, admin_token, agent_token, agent_user):
    resp = client.get("/reports/dashboard", headers=auth_headers(admin_token))
    data = resp.json()
    assert "total_agents" in data
    assert data["total_agents"] == 1
    assert "activity_today" in data
    assert data["activity_today"] >= 1  # حداقل همان لاگین مشاور


def test_dashboard_agent_does_not_see_admin_only_fields(client, agent_token):
    resp = client.get("/reports/dashboard", headers=auth_headers(agent_token))
    data = resp.json()
    assert "total_agents" not in data
    assert "activity_today" not in data
