import re
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.http_security import withdrawal_rate_limiter
from app.modules.arrepentimiento import service as withdrawal_service
from app.modules.arrepentimiento.models import WithdrawalRequest
from app.modules.cuenta.service import AccountService
from app.modules.modulos.models import ModulePurchase

pytestmark = pytest.mark.asyncio

URL = "/api/v1/arrepentimiento"
CODE_RE = re.compile(r"^ARR-[ABCDEFGHJKMNPQRSTUVWXYZ23456789]{6}$")


def _payload(**overrides):
    data = {
        "full_name": "  Ana Perez ",
        "email": "ana@example.com",
        "purchase_detail": "Plantilla Estudio, 3/10, operación MP 123456",
        "message": "Me equivoqué de plantilla",
    }
    data.update(overrides)
    return data


@pytest.fixture(autouse=True)
def _capture_notifications(monkeypatch):
    """Intercepta mail y Telegram: ningun test sale a la red."""
    sent = {"emails": [], "alerts": []}

    async def fake_email(to, code, full_name):
        sent["emails"].append((to, code, full_name))
        return True

    async def fake_alert(message, event_type="default"):
        sent["alerts"].append((message, event_type))

    monkeypatch.setattr(withdrawal_service, "send_withdrawal_confirmation_email", fake_email)
    monkeypatch.setattr(withdrawal_service, "send_telegram_alert", fake_alert)
    return sent


async def test_public_request_without_auth_returns_code_and_persists(
    client, db_session, _capture_notifications
):
    resp = await client.post(URL, json=_payload())

    assert resp.status_code == 201
    body = resp.json()
    assert CODE_RE.match(body["code"])
    assert body["created_at"]

    rows = (await db_session.execute(select(WithdrawalRequest))).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.code == body["code"]
    assert row.full_name == "Ana Perez"  # strip
    assert row.email == "ana@example.com"
    assert row.user_id is None
    assert row.status == "pending"
    assert row.created_at is not None


async def test_sends_confirmation_email_and_operator_alert(client, _capture_notifications):
    resp = await client.post(URL, json=_payload())
    code = resp.json()["code"]

    assert _capture_notifications["emails"] == [("ana@example.com", code, "Ana Perez")]
    assert len(_capture_notifications["alerts"]) == 1
    message, event_type = _capture_notifications["alerts"][0]
    assert code in message
    # event_type propio: el cooldown de Telegram no tiene que taparle el aviso
    # a un pedido distinto.
    assert event_type == f"withdrawal:{code}"


async def test_message_is_optional(client, db_session):
    resp = await client.post(URL, json=_payload(message="   "))
    assert resp.status_code == 201
    row = (await db_session.execute(select(WithdrawalRequest))).scalar_one()
    assert row.message is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"email": "no-es-un-mail"},
        {"full_name": ""},
        {"full_name": "   "},
        {"purchase_detail": ""},
        {"purchase_detail": "   "},
        {"full_name": "x" * 121},
        {"purchase_detail": "x" * 1001},
        {"message": "x" * 2001},
    ],
)
async def test_validation_errors(client, db_session, overrides):
    resp = await client.post(URL, json=_payload(**overrides))
    assert resp.status_code == 422
    assert (await db_session.execute(select(WithdrawalRequest))).first() is None


@pytest.mark.parametrize("missing", ["full_name", "email", "purchase_detail"])
async def test_missing_required_fields(client, missing):
    data = _payload()
    del data[missing]
    resp = await client.post(URL, json=data)
    assert resp.status_code == 422


async def test_with_session_links_user(api_auth_client, test_user, db_session):
    resp = await api_auth_client.post(URL, json=_payload())

    assert resp.status_code == 201
    row = (await db_session.execute(select(WithdrawalRequest))).scalar_one()
    assert row.user_id == str(test_user.id)


async def test_invalid_session_does_not_block_request(client, db_session):
    resp = await client.post(
        URL, json=_payload(), headers={"Authorization": "Bearer token-invalido"}
    )
    assert resp.status_code == 201
    row = (await db_session.execute(select(WithdrawalRequest))).scalar_one()
    assert row.user_id is None


async def test_codes_are_unique_and_well_formed(client, db_session):
    for _ in range(4):
        assert (await client.post(URL, json=_payload())).status_code == 201

    codes = (await db_session.execute(select(WithdrawalRequest.code))).scalars().all()
    assert len(set(codes)) == 4
    assert all(CODE_RE.match(c) for c in codes)


async def test_generate_code_avoids_ambiguous_characters():
    for _ in range(200):
        code = withdrawal_service.generate_code()
        assert CODE_RE.match(code)
        assert not set(code[4:]) & set("0O1IL")


async def test_code_collision_is_retried(client, db_session, monkeypatch):
    first = (await client.post(URL, json=_payload())).json()["code"]
    candidates = iter([first, first, "ARR-ZZZZZZ"])
    monkeypatch.setattr(withdrawal_service, "generate_code", lambda: next(candidates))

    resp = await client.post(URL, json=_payload(email="otra@example.com"))

    assert resp.status_code == 201
    assert resp.json()["code"] == "ARR-ZZZZZZ"


async def test_email_failure_does_not_break_request(client, db_session, monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("resend caido")

    monkeypatch.setattr(withdrawal_service, "send_withdrawal_confirmation_email", boom)

    resp = await client.post(URL, json=_payload())

    assert resp.status_code == 201
    assert (await db_session.execute(select(WithdrawalRequest))).scalar_one()


async def test_telegram_failure_does_not_break_request(client, db_session, monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("telegram caido")

    monkeypatch.setattr(withdrawal_service, "send_telegram_alert", boom)

    resp = await client.post(URL, json=_payload())

    assert resp.status_code == 201
    assert (await db_session.execute(select(WithdrawalRequest))).scalar_one()


async def test_rate_limited_by_ip(client, monkeypatch):
    monkeypatch.setattr(withdrawal_rate_limiter, "max_attempts", 2)

    assert (await client.post(URL, json=_payload())).status_code == 201
    assert (await client.post(URL, json=_payload())).status_code == 201
    blocked = await client.post(URL, json=_payload())

    assert blocked.status_code == 429
    assert "retry-after" in {k.lower() for k in blocked.headers.keys()}


async def test_old_purchase_is_flagged_for_review_but_accepted(
    api_auth_client, test_user, db_session
):
    db_session.add(
        ModulePurchase(
            user_id=str(test_user.id),
            module_key="study",
            amount_paid=1500,
            created_at=datetime.now(timezone.utc) - timedelta(days=30),
        )
    )
    await db_session.commit()

    resp = await api_auth_client.post(URL, json=_payload())

    assert resp.status_code == 201
    row = (await db_session.execute(select(WithdrawalRequest))).scalar_one()
    assert row.needs_review is True


async def test_recent_purchase_is_not_flagged(api_auth_client, test_user, db_session):
    db_session.add(
        ModulePurchase(
            user_id=str(test_user.id),
            module_key="study",
            amount_paid=1500,
            created_at=datetime.now(timezone.utc) - timedelta(days=3),
        )
    )
    await db_session.commit()

    await api_auth_client.post(URL, json=_payload())

    row = (await db_session.execute(select(WithdrawalRequest))).scalar_one()
    assert row.needs_review is False


async def test_old_purchase_matched_by_email_without_session(client, test_user, db_session):
    db_session.add(
        ModulePurchase(
            user_id=str(test_user.id),
            module_key="study",
            created_at=datetime.now(timezone.utc) - timedelta(days=20),
        )
    )
    await db_session.commit()

    resp = await client.post(URL, json=_payload(email="TEST@test.com"))

    assert resp.status_code == 201
    row = (await db_session.execute(select(WithdrawalRequest))).scalar_one()
    assert row.needs_review is True
    # Sin sesion no se vincula la cuenta: el email solo sirve para la marca.
    assert row.user_id is None


async def test_account_deletion_keeps_request_detached(
    api_auth_client, test_user, db_session
):
    await api_auth_client.post(URL, json=_payload())

    await AccountService(db_session).delete_account(test_user)

    row = (await db_session.execute(select(WithdrawalRequest))).scalar_one()
    assert row.user_id is None
    assert row.email == "ana@example.com"


async def test_confirmation_email_has_code_and_escapes_name(monkeypatch):
    from app.core import email as email_module

    captured = {}

    async def fake_send(to, subject, html):
        captured.update(to=to, subject=subject, html=html)
        return True

    monkeypatch.setattr(email_module, "send_email", fake_send)

    await email_module.send_withdrawal_confirmation_email(
        "ana@example.com", "ARR-ABC234", "<script>alert(1)</script>"
    )

    assert captured["to"] == "ana@example.com"
    assert "ARR-ABC234" in captured["subject"]
    assert "ARR-ABC234" in captured["html"]
    assert "<script>" not in captured["html"]
    assert "5 días hábiles" in captured["html"]
