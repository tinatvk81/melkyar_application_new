from tests.conftest import auth_headers


def _create_property(client, token, **overrides):
    payload = {"deal_type": "sale", "city": "تهران", "address": "آدرس تست", "details": {"price": 1000000000}}
    payload.update(overrides)
    resp = client.post("/properties/", json=payload, headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_filter_by_city(client, agent_token):
    _create_property(client, agent_token, city="تهران")
    _create_property(client, agent_token, city="شیراز")

    resp = client.get("/properties/", params={"city": "شیراز"}, headers=auth_headers(agent_token))
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["city"] == "شیراز"


def test_filter_by_deal_type(client, agent_token):
    _create_property(client, agent_token, deal_type="sale")
    _create_property(client, agent_token, deal_type="rent", details={"monthly_rent": 5000000})

    resp = client.get("/properties/", params={"deal_type": "rent"}, headers=auth_headers(agent_token))
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["deal_type"] == "rent"


def test_price_range_filter_across_deal_types(client, agent_token):
    """قیمت برای هر نوع معامله در فیلد متفاوتی از JSON ذخیره می‌شود؛ فیلتر باید همه را پوشش دهد."""
    _create_property(client, agent_token, city="ارزان", deal_type="sale", details={"price": 1_000_000_000})
    _create_property(client, agent_token, city="گران", deal_type="sale", details={"price": 9_000_000_000})
    # عمداً یک مبلغ اجاره در همان بازه‌ی عددی گذاشته شده تا مکانیزم COALESCE
    # را تست کند، نه این‌که واقع‌بینانه باشد (اجاره‌ی واقعی معمولاً میلیونی و
    # قیمت فروش میلیاردی است — این دو عدد در دنیای واقعی هرگز در یک بازه‌ی
    # مقایسه قرار نمی‌گیرند، ولی این‌جا فقط منطق فیلتر را می‌سنجیم)
    _create_property(client, agent_token, city="اجاره", deal_type="rent", details={"monthly_rent": 1_500_000_000})

    resp = client.get("/properties/", params={"min_price": 500_000_000, "max_price": 2_000_000_000}, headers=auth_headers(agent_token))
    data = resp.json()
    cities = {p["city"] for p in data["items"]}
    assert cities == {"ارزان", "اجاره"}  # هردو داخل بازه‌اند؛ «گران» (۹ میلیارد) نباید باشد


def test_free_text_search_across_fields(client, agent_token):
    _create_property(client, agent_token, address="خیابان ولیعصر", owner_name="احمد رضایی", owner_phone="09121112233")
    _create_property(client, agent_token, address="بلوار زند", owner_name="مریم احمدی", owner_phone="09354445566")
    _create_property(client, agent_token, address="میدان آزادی", owner_name="سارا کریمی", owner_phone="09121112233")

    # جستجوی «احمد» باید هر دو مالک «احمد رضایی» و «مریم احمدی» را پیدا کند
    resp = client.get("/properties/", params={"search": "احمد"}, headers=auth_headers(agent_token))
    assert resp.json()["total"] == 2

    # جستجوی شماره تلفن باید هر دو فایل با آن شماره را پیدا کند
    resp2 = client.get("/properties/", params={"search": "09121112233"}, headers=auth_headers(agent_token))
    assert resp2.json()["total"] == 2

    # جستجوی کلیدواژه‌ی ناموجود باید صفر نتیجه بدهد
    resp3 = client.get("/properties/", params={"search": "xyz_not_found"}, headers=auth_headers(agent_token))
    assert resp3.json()["total"] == 0


def test_sort_by_price_ascending(client, agent_token):
    _create_property(client, agent_token, city="ارزان", details={"price": 1_000_000_000})
    _create_property(client, agent_token, city="متوسط", details={"price": 5_000_000_000})
    _create_property(client, agent_token, city="گران", details={"price": 9_000_000_000})

    resp = client.get("/properties/", params={"sort_by": "price", "sort_order": "asc"}, headers=auth_headers(agent_token))
    cities_in_order = [p["city"] for p in resp.json()["items"]]
    assert cities_in_order == ["ارزان", "متوسط", "گران"]


def test_pagination_respects_page_size(client, agent_token):
    for i in range(5):
        _create_property(client, agent_token, city=f"شهر{i}")

    resp = client.get("/properties/", params={"page": 1, "page_size": 2}, headers=auth_headers(agent_token))
    data = resp.json()
    assert data["total"] == 5
    assert data["page_size"] == 2
    assert data["total_pages"] == 3
    assert len(data["items"]) == 2
