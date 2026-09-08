"""
این تست‌ها ارسال واقعی پیامک را چک نمی‌کنند (چون نیاز به حساب واقعی و پولی
نزد یک سرویس‌دهنده دارد) — درخواست HTTP به سرویس پیامک را mock می‌کنند تا
منطق برنامه (چه زمانی، به چه کسی، با چه متنی) تست شود.
"""
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from tests.conftest import auth_headers
from app.services import sms_service
from app.services.reminder_job import build_reminder_message, run_daily_reminder_job
from app.models.property import Property, DealType


def test_send_sms_disabled_by_default(monkeypatch):
    monkeypatch.setattr(sms_service.settings, "SMS_ENABLED", False)
    result = sms_service.send_sms("09121234567", "پیام تست")
    assert result is False


def test_send_sms_enabled_but_no_api_key(monkeypatch):
    monkeypatch.setattr(sms_service.settings, "SMS_ENABLED", True)
    monkeypatch.setattr(sms_service.settings, "SMS_API_KEY", "")
    result = sms_service.send_sms("09121234567", "پیام تست")
    assert result is False


def test_send_sms_success_with_mocked_http(monkeypatch):
    monkeypatch.setattr(sms_service.settings, "SMS_ENABLED", True)
    monkeypatch.setattr(sms_service.settings, "SMS_API_KEY", "fake-api-key-for-test")
    monkeypatch.setattr(sms_service.settings, "SMS_SENDER_LINE", "")

    mock_response = MagicMock()
    mock_response.status_code = 200
    with patch("app.services.sms_service.requests.get", return_value=mock_response) as mock_get:
        result = sms_service.send_sms("09121234567", "قرارداد شما رو‌به‌اتمام است")

    assert result is True
    mock_get.assert_called_once()
    called_url = mock_get.call_args[0][0]
    called_params = mock_get.call_args[1]["params"]
    assert "fake-api-key-for-test" in called_url
    assert called_params["receptor"] == "09121234567"
    assert "قرارداد" in called_params["message"]


def test_send_sms_handles_http_failure(monkeypatch):
    monkeypatch.setattr(sms_service.settings, "SMS_ENABLED", True)
    monkeypatch.setattr(sms_service.settings, "SMS_API_KEY", "fake-key")

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    with patch("app.services.sms_service.requests.get", return_value=mock_response):
        result = sms_service.send_sms("09121234567", "پیام")
    assert result is False


def test_send_sms_handles_connection_error(monkeypatch):
    monkeypatch.setattr(sms_service.settings, "SMS_ENABLED", True)
    monkeypatch.setattr(sms_service.settings, "SMS_API_KEY", "fake-key")

    import requests
    with patch("app.services.sms_service.requests.get", side_effect=requests.ConnectionError("no network")):
        result = sms_service.send_sms("09121234567", "پیام")
    assert result is False


def test_build_reminder_message_format():
    fake_prop = Property(
        city="تهران", address="خیابان ولیعصر",
        contract_end_date=date.today() + timedelta(days=2),
        deal_type=DealType.rent,
    )
    message = build_reminder_message("مشاور تست", [fake_prop])
    assert "مشاور تست" in message
    assert "تهران" in message
    assert "خیابان ولیعصر" in message
    assert "2 روز" in message


def test_reminder_job_skips_when_disabled(db_session, monkeypatch):
    monkeypatch.setattr("app.services.reminder_job.settings.SMS_ENABLED", False)
    result = run_daily_reminder_job(db_session)
    assert result == {"enabled": False, "agents_checked": 0, "sms_sent": 0}


def test_reminder_job_only_texts_agents_with_phone_and_urgent_contracts(
    client, db_session, agent_token, agent2_token, agent_user, agent2_user, monkeypatch
):
    monkeypatch.setattr("app.services.reminder_job.settings.SMS_ENABLED", True)
    monkeypatch.setattr("app.services.reminder_job.settings.SMS_URGENT_DAYS_THRESHOLD", 3)

    # مشاور یک: شماره تلفن دارد + یک قرارداد فوری (۲ روز مانده)
    agent_user.phone = "09121234567"
    db_session.commit()
    client.post(
        "/properties/",
        json={
            "deal_type": "rent", "city": "تهران", "address": "فوری",
            "contract_end_date": (date.today() + timedelta(days=2)).isoformat(),
            "details": {"monthly_rent": 5000000},
        },
        headers=auth_headers(agent_token),
    )

    # مشاور دو: شماره تلفن ندارد (نباید پیامک بگیرد حتی با قرارداد فوری)
    client.post(
        "/properties/",
        json={
            "deal_type": "rent", "city": "شیراز", "address": "فوری ولی بدون شماره",
            "contract_end_date": (date.today() + timedelta(days=1)).isoformat(),
            "details": {"monthly_rent": 4000000},
        },
        headers=auth_headers(agent2_token),
    )

    with patch("app.services.reminder_job.send_sms", return_value=True) as mock_send:
        result = run_daily_reminder_job(db_session)

    assert result["enabled"] is True
    assert result["sms_sent"] == 1  # فقط مشاور یک
    mock_send.assert_called_once()
    called_phone = mock_send.call_args[0][0]
    called_message = mock_send.call_args[0][1]
    assert called_phone == "09121234567"
    assert "فوری" in called_message


def test_reminder_job_skips_non_urgent_contracts(client, db_session, agent_token, agent_user, monkeypatch):
    monkeypatch.setattr("app.services.reminder_job.settings.SMS_ENABLED", True)
    monkeypatch.setattr("app.services.reminder_job.settings.SMS_URGENT_DAYS_THRESHOLD", 3)

    agent_user.phone = "09121234567"
    db_session.commit()

    # قرارداد ۲۰ روزه — فوری نیست (آستانه ۳ روز است)
    client.post(
        "/properties/",
        json={
            "deal_type": "rent", "city": "تهران",
            "contract_end_date": (date.today() + timedelta(days=20)).isoformat(),
            "details": {"monthly_rent": 5000000},
        },
        headers=auth_headers(agent_token),
    )

    with patch("app.services.reminder_job.send_sms", return_value=True) as mock_send:
        result = run_daily_reminder_job(db_session)

    assert result["sms_sent"] == 0
    mock_send.assert_not_called()


def test_agent_cannot_trigger_sms_reminders(client, agent_token):
    resp = client.post("/reports/trigger-sms-reminders", headers=auth_headers(agent_token))
    assert resp.status_code == 403


def test_admin_can_trigger_sms_reminders(client, admin_token):
    resp = client.post("/reports/trigger-sms-reminders", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    assert "sms_sent" in resp.json()
