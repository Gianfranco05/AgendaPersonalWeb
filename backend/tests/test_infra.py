from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
def mock_config():
    from app.infra.config import InfraConfig, DreamMachineConfig, LedsConfig, LedDeviceConfig
    config = InfraConfig(
        dream_machine=DreamMachineConfig(host="192.168.1.1", username="root"),
        leds=LedsConfig(
            type="wled",
            devices=[LedDeviceConfig(name="test", host="192.168.1.100")],
        ),
    )
    with patch("app.infra.router.get_infra_config", return_value=config):
        yield


@pytest.fixture
def mock_no_dm_config():
    from app.infra.config import InfraConfig, LedsConfig
    config = InfraConfig(leds=LedsConfig())
    with patch("app.infra.router.get_infra_config", return_value=config):
        yield


@pytest_asyncio.fixture
async def http_client(client, db_session, test_user):
    """Cliente logueado como superusuario: el endpoint solo lo permite al operador."""
    test_user.is_superuser = True
    await db_session.commit()
    await client.post("/auth/api/login", json={"email": "test@test.com", "password": "test123"})
    return client


@pytest.mark.asyncio
async def test_shutdown_requires_login(client, mock_config):
    with patch("app.infra.service.DreamMachineService.shutdown", new_callable=AsyncMock) as shutdown:
        response = await client.post("/api/v1/infra/shutdown")
    assert response.status_code == 401
    shutdown.assert_not_awaited()


@pytest.mark.asyncio
async def test_shutdown_forbidden_for_regular_user(api_auth_client, mock_config):
    with patch("app.infra.service.DreamMachineService.shutdown", new_callable=AsyncMock) as shutdown:
        response = await api_auth_client.post("/api/v1/infra/shutdown")
    assert response.status_code == 403
    shutdown.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_api_route_is_public_by_accident():
    """Toda ruta de /api/v1 exige sesion salvo las publicas a proposito."""
    from fastapi.routing import APIRoute

    from app.core.dependencies import get_current_user

    def deps(dep, acc):
        acc.add(dep.call)
        for sub in dep.dependencies:
            deps(sub, acc)

    public = {
        "/api/v1/billing/webhook",
        "/api/v1/billing/webhook/mercadopago",
        "/api/v1/arrepentimiento",
    }
    abiertas = []
    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/api/v1"):
            continue
        acc: set = set()
        deps(route.dependant, acc)
        names = {getattr(c, "__name__", "") for c in acc}
        if route.path not in public and not ({"get_current_user", "_require"} & names):
            abiertas.append(route.path)
    assert abiertas == []


@pytest.mark.asyncio
async def test_shutdown_success(http_client, mock_config):
    with (
        patch("app.infra.service.DreamMachineService.shutdown", new_callable=AsyncMock) as mock_shutdown,
        patch("app.infra.led_controller.WledController.turn_off", new_callable=AsyncMock) as mock_led,
    ):
        mock_shutdown.return_value = "OK"
        mock_led.return_value = True

        response = await http_client.post("/api/v1/infra/shutdown")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "Shutdown command sent" in data["message"]
    mock_shutdown.assert_awaited_once()
    mock_led.assert_awaited_once()


@pytest.mark.asyncio
async def test_shutdown_dm_unreachable(http_client, mock_config):
    from app.infra.service import DreamMachineShutdownError

    with patch(
        "app.infra.service.DreamMachineService.shutdown",
        new_callable=AsyncMock,
        side_effect=DreamMachineShutdownError("Host unreachable"),
    ):
        response = await http_client.post("/api/v1/infra/shutdown")

    assert response.status_code == 502
    assert "Host unreachable" in response.json()["detail"]


@pytest.mark.asyncio
async def test_shutdown_not_configured(http_client, mock_no_dm_config):
    response = await http_client.post("/api/v1/infra/shutdown")

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


@pytest.mark.asyncio
async def test_shutdown_led_failure_nonfatal(http_client, mock_config):
    with patch(
        "app.infra.service.DreamMachineService.shutdown",
        new_callable=AsyncMock,
    ) as mock_shutdown, patch(
        "app.infra.led_controller.WledController.turn_off",
        new_callable=AsyncMock,
        side_effect=ConnectionError("LED timeout"),
    ):
        mock_shutdown.return_value = "OK"
        response = await http_client.post("/api/v1/infra/shutdown")

    assert response.status_code == 200
    assert "Shutdown command sent" in response.json()["message"]
    mock_shutdown.assert_awaited_once()
