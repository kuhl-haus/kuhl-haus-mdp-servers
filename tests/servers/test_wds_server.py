"""Unit tests for the 'get' cache action in wds_server.py.

Focuses on the limit parameter extraction and pass-through to get_cache().
"""
import json
import pytest
from asgi_lifespan import LifespanManager
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport

MODULE = "kuhl_haus.servers.wds_server"

from kuhl_haus.servers.wds_server import app, settings  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_wds_service(cache_data=None):
    """Return a mock WidgetDataService."""
    mock = AsyncMock()
    mock.subscribe = AsyncMock()
    mock.unsubscribe = AsyncMock()
    mock.get_cache = AsyncMock(return_value=cache_data or [])
    mock.disconnect = AsyncMock()
    mock._handle_pubsub = AsyncMock()
    return mock


# ---------------------------------------------------------------------------
# get action — limit param
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch(f"{MODULE}.wds_service")
async def test_wds_get_with_no_limit_expect_get_cache_called_without_limit(
    mock_service,
):
    """get action with no limit field calls get_cache with default limit=0."""
    # Arrange
    mock_service.get_cache = AsyncMock(return_value=[{"title": "Article 1"}])
    mock_service.disconnect = AsyncMock()
    mock_service._handle_pubsub = AsyncMock()

    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with patch.object(settings, "auth_enabled", False):
                async with client.websocket_connect("/ws") as ws:
                    # Act
                    await ws.send_text(json.dumps({
                        "action": "get",
                        "cache": "news:feed:latest",
                    }))
                    response = json.loads(await ws.receive_text())

    # Assert
    assert response["cache"] == "news:feed:latest"
    mock_service.get_cache.assert_called_once_with(
        "news:feed:latest", limit=0
    )


@pytest.mark.asyncio
@patch(f"{MODULE}.wds_service")
async def test_wds_get_with_limit_expect_get_cache_called_with_limit(
    mock_service,
):
    """get action with limit field passes limit to get_cache."""
    # Arrange
    mock_service.get_cache = AsyncMock(return_value=[{"title": "Article 1"}])
    mock_service.disconnect = AsyncMock()
    mock_service._handle_pubsub = AsyncMock()

    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with patch.object(settings, "auth_enabled", False):
                async with client.websocket_connect("/ws") as ws:
                    # Act
                    await ws.send_text(json.dumps({
                        "action": "get",
                        "cache": "news:feed:latest",
                        "limit": 500,
                    }))
                    response = json.loads(await ws.receive_text())

    # Assert
    assert response["cache"] == "news:feed:latest"
    mock_service.get_cache.assert_called_once_with(
        "news:feed:latest", limit=500
    )
