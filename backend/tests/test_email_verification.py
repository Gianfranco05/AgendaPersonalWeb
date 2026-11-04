from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.core.security import hash_refresh_token, verify_password
from app.modules.auth.models import (
    RefreshToken,
    User,
    VerificationPurpose,
    VerificationToken,
)
from app.modules.auth.verification_service import VerificationService

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def registered(client):
    resp = await client.post("/auth/api/register", json={
        "email": "nuevo@test.com",
        "full_name": "Nuevo",
        "password": "password123",
        "accept_terms": True,
        "confirm_age": True,
    })
    assert resp.status_code == 201
    return client, resp.json()


async def _issue(db_session, user_id: str, purpose: str) -> str:
    return await VerificationService(db_session).issue(user_id, purpose)


async def _expire(db_session, raw_token: str) -> None:
    result = await db_session.execute(
        select(VerificationToken).where(
            VerificationToken.token_hash == hash_refresh_token(raw_token)
        )
    )
    token = result.scalar_one()
    token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await db_session.commit()


# ── Verificación de email ────────────────────────────────────────────────────

async def test_new_user_starts_unverified(registered):
    client, _ = registered
    me = await client.get("/auth/api/me")
    assert me.json()["is_verified"] is False


async def test_register_creates_verification_token(registered, db_session):
    _, data = registered
    result = await db_session.execute(
        select(VerificationToken).where(
            VerificationToken.user_id == data["id"],
            VerificationToken.purpose == VerificationPurpose.EMAIL_VERIFY,
        )
    )
    assert result.scalar_one_or_none() is not None


async def test_verify_email_marks_user_verified(registered, db_session):
    client, data = registered
    token = await _issue(db_session, data["id"], VerificationPurpose.EMAIL_VERIFY)

    resp = await client.post("/auth/api/verify-email", json={"token": token})
    assert resp.status_code == 200
    assert resp.json()["is_verified"] is True

    me = await client.get("/auth/api/me")
    assert me.json()["is_verified"] is True


async def test_verification_token_is_single_use(registered, db_session):
    client, data = registered
    token = await _issue(db_session, data["id"], VerificationPurpose.EMAIL_VERIFY)

    assert (await client.post("/auth/api/verify-email", json={"token": token})).status_code == 200
    replay = await client.post("/auth/api/verify-email", json={"token": token})
    assert replay.status_code == 400


async def test_expired_verification_token_rejected(registered, db_session):
    client, data = registered
    token = await _issue(db_session, data["id"], VerificationPurpose.EMAIL_VERIFY)
    await _expire(db_session, token)

    resp = await client.post("/auth/api/verify-email", json={"token": token})
    assert resp.status_code == 400


async def test_invalid_verification_token_rejected(client, test_user):
    resp = await client.post("/auth/api/verify-email", json={"token": "no-existe"})
    assert resp.status_code == 400


async def test_requesting_new_link_invalidates_the_previous_one(registered, db_session):
    client, data = registered
    first = await _issue(db_session, data["id"], VerificationPurpose.EMAIL_VERIFY)
    second = await _issue(db_session, data["id"], VerificationPurpose.EMAIL_VERIFY)

    assert (await client.post("/auth/api/verify-email", json={"token": first})).status_code == 400
    assert (await client.post("/auth/api/verify-email", json={"token": second})).status_code == 200


async def test_verify_request_is_noop_for_already_verified_user(registered, db_session):
    client, data = registered
    token = await _issue(db_session, data["id"], VerificationPurpose.EMAIL_VERIFY)
    await client.post("/auth/api/verify-email", json={"token": token})

    resp = await client.post("/auth/api/verify-email/request")
    assert resp.status_code == 200
    assert resp.json()["already_verified"] is True


# ── Reset de contraseña ──────────────────────────────────────────────────────

async def test_forgot_password_responds_the_same_for_unknown_email(client, test_user):
    known = await client.post("/auth/api/forgot-password", json={"email": "test@test.com"})
    unknown = await client.post("/auth/api/forgot-password", json={"email": "nadie@test.com"})

    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()


async def test_forgot_password_creates_token_only_for_real_user(client, test_user, db_session):
    await client.post("/auth/api/forgot-password", json={"email": "test@test.com"})
    result = await db_session.execute(
        select(VerificationToken).where(
            VerificationToken.purpose == VerificationPurpose.PASSWORD_RESET
        )
    )
    tokens = result.scalars().all()
    assert len(tokens) == 1
    assert tokens[0].user_id == test_user.id


async def test_reset_password_changes_the_password(client, test_user, db_session):
    token = await _issue(db_session, test_user.id, VerificationPurpose.PASSWORD_RESET)

    resp = await client.post("/auth/api/reset-password", json={
        "token": token,
        "password": "nuevapass456",
    })
    assert resp.status_code == 200

    old_login = await client.post("/auth/api/login", json={
        "email": "test@test.com",
        "password": "test123",
    })
    assert old_login.status_code == 401

    new_login = await client.post("/auth/api/login", json={
        "email": "test@test.com",
        "password": "nuevapass456",
    })
    assert new_login.status_code == 200


async def test_reset_password_revokes_all_sessions(client, test_user, db_session):
    login = await client.post("/auth/api/login", json={
        "email": "test@test.com",
        "password": "test123",
    })
    old_refresh = login.json()["refresh_token"]

    token = await _issue(db_session, test_user.id, VerificationPurpose.PASSWORD_RESET)
    await client.post("/auth/api/reset-password", json={
        "token": token,
        "password": "nuevapass456",
    })

    # La sesion abierta con la contraseña vieja no puede sobrevivir al cambio.
    resp = await client.post("/auth/api/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 401

    result = await db_session.execute(
        select(RefreshToken).where(RefreshToken.user_id == test_user.id)
    )
    assert all(t.revoked_at is not None for t in result.scalars().all())


async def test_reset_token_is_single_use(client, test_user, db_session):
    token = await _issue(db_session, test_user.id, VerificationPurpose.PASSWORD_RESET)

    first = await client.post("/auth/api/reset-password", json={
        "token": token, "password": "nuevapass456",
    })
    assert first.status_code == 200

    replay = await client.post("/auth/api/reset-password", json={
        "token": token, "password": "otramas789",
    })
    assert replay.status_code == 400


async def test_expired_reset_token_rejected(client, test_user, db_session):
    token = await _issue(db_session, test_user.id, VerificationPurpose.PASSWORD_RESET)
    await _expire(db_session, token)

    resp = await client.post("/auth/api/reset-password", json={
        "token": token, "password": "nuevapass456",
    })
    assert resp.status_code == 400


async def test_verification_token_cannot_be_used_to_reset_password(
    client, test_user, db_session
):
    # Los propositos no son intercambiables: un link de "confirmá tu email"
    # no puede servir para cambiar la contraseña.
    token = await _issue(db_session, test_user.id, VerificationPurpose.EMAIL_VERIFY)

    resp = await client.post("/auth/api/reset-password", json={
        "token": token, "password": "nuevapass456",
    })
    assert resp.status_code == 400


async def test_reset_password_rejects_short_password(client, test_user, db_session):
    token = await _issue(db_session, test_user.id, VerificationPurpose.PASSWORD_RESET)
    resp = await client.post("/auth/api/reset-password", json={
        "token": token, "password": "123",
    })
    assert resp.status_code == 422


async def test_password_is_stored_hashed_after_reset(client, test_user, db_session):
    token = await _issue(db_session, test_user.id, VerificationPurpose.PASSWORD_RESET)
    await client.post("/auth/api/reset-password", json={
        "token": token, "password": "nuevapass456",
    })

    user = await db_session.get(User, test_user.id)
    await db_session.refresh(user)
    assert user.password_hash != "nuevapass456"
    assert verify_password("nuevapass456", user.password_hash)
