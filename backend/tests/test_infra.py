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
async def http_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


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
