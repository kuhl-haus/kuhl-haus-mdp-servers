"""Unit tests for the 'get' cache action in wds_server.py.

Focuses on the limit parameter extraction and pass-through to get_cache().
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.testclient import TestClient

MODULE = "kuhl_haus.servers.wds_server"

from kuhl_haus.servers.wds_server import app, settings  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_wds_service(cache_data=None):
    """Return a mock WidgetDataService."""
    mock = MagicMock()
    mock.start = AsyncMock()
    mock.stop = AsyncMock()
    mock.subscribe = AsyncMock()
    mock.unsubscribe = AsyncMock()
    mock.get_cache = AsyncMock(return_value=cache_data or [])
    mock.disconnect = AsyncMock()
    return mock


def _make_mock_redis():
    mock = AsyncMock()
    mock.close = AsyncMock()
    mock.pubsub = MagicMock(return_value=AsyncMock())
    return mock


# ---------------------------------------------------------------------------
# get action — limit param
# ---------------------------------------------------------------------------


def test_wds_get_with_no_limit_expect_get_cache_called_with_zero():
    """get action with no limit field calls get_cache(cache_key, limit=0)."""
    # Arrange
    mock_service = _make_mock_wds_service(cache_data=[{"title": "Article 1"}])
    mock_redis = _make_mock_redis()

    with patch(f"{MODULE}.redis") as mock_redis_module, \
         patch(f"{MODULE}.WidgetDataService", return_value=mock_service), \
         patch.object(settings, "auth_enabled", False):
        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        with TestClient(app) as client:
            with client.websocket_connect("/ws") as ws:
                # Act
                ws.send_text(json.dumps({
                    "action": "get",
                    "cache": "news:feed:latest",
                }))
                response = json.loads(ws.receive_text())

    # Assert
    assert response["cache"] == "news:feed:latest"
    mock_service.get_cache.assert_called_once_with("news:feed:latest", limit=0)


def test_wds_get_with_limit_expect_get_cache_called_with_limit():
    """get action with limit field passes integer limit to get_cache."""
    # Arrange
    mock_service = _make_mock_wds_service(cache_data=[{"title": "Article 1"}])
    mock_redis = _make_mock_redis()

    with patch(f"{MODULE}.redis") as mock_redis_module, \
         patch(f"{MODULE}.WidgetDataService", return_value=mock_service), \
         patch.object(settings, "auth_enabled", False):
        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        with TestClient(app) as client:
            with client.websocket_connect("/ws") as ws:
                # Act
                ws.send_text(json.dumps({
                    "action": "get",
                    "cache": "news:feed:latest",
                    "limit": 500,
                }))
                response = json.loads(ws.receive_text())

    # Assert
    assert response["cache"] == "news:feed:latest"
    mock_service.get_cache.assert_called_once_with("news:feed:latest", limit=500)
