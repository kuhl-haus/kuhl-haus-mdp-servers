"""Unit tests for kuhl_haus.servers.mds_server.

Run:
    pytest tests/servers/test_mds_server.py -v
"""
import pytest
from asgi_lifespan import LifespanManager
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

MODULE = "kuhl_haus.servers.mds_server"

from kuhl_haus.servers.mds_server import app, settings  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_scanner():
    mock = AsyncMock()
    mock.mdc_connected = True
    mock.running = True
    mock.processed = 0
    mock.published_results = 0
    mock.empty_results = 0
    mock.decoding_errors = 0
    mock.errors = 0
    mock.restarts = 0
    mock.start = AsyncMock()
    mock.stop = AsyncMock()
    return mock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def client():
    """AsyncClient with mocked MarketDataScanner."""
    mock_scanner = _make_mock_scanner()

    with patch(f"{MODULE}.MarketDataScanner", return_value=mock_scanner):
        async with LifespanManager(app):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as ac:
                yield ac, mock_scanner


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

def test_mds_settings_with_default_wdc_redis_url_expect_local_redis_db1():
    assert settings.wdc_redis_url == "redis://mdc:mdc@localhost:6379/1"


def test_mds_settings_with_default_server_port_expect_4205():
    assert settings.server_port == 4205


def test_mds_settings_with_default_log_level_expect_info():
    assert settings.log_level == "INFO"


def test_mds_settings_with_default_massive_api_key_expect_empty():
    assert settings.massive_api_key == ""


@pytest.mark.parametrize("attr", [
    "wdc_redis_url",
    "massive_api_key",
    "server_ip",
    "server_port",
    "log_level",
    "container_image",
    "image_version",
])
def test_mds_settings_with_attr_expect_exists(attr):
    assert hasattr(settings, attr)


# ---------------------------------------------------------------------------
# Lifespan — startup
# ---------------------------------------------------------------------------

async def test_mds_lifespan_with_default_settings_expect_scanner_started():
    mock_scanner = _make_mock_scanner()

    with patch(f"{MODULE}.MarketDataScanner", return_value=mock_scanner) as mock_cls:
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test"):
                pass

    mock_cls.assert_called_once()
    mock_scanner.start.assert_awaited_once()


async def test_mds_lifespan_with_default_settings_expect_wdc_redis_url_passed():
    mock_scanner = _make_mock_scanner()

    with patch(f"{MODULE}.MarketDataScanner", return_value=mock_scanner) as mock_cls:
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test"):
                pass

    call_kwargs = mock_cls.call_args.kwargs
    assert call_kwargs["redis_url"] == settings.wdc_redis_url


async def test_mds_lifespan_with_default_settings_expect_quote_subscription():
    mock_scanner = _make_mock_scanner()

    with patch(f"{MODULE}.MarketDataScanner", return_value=mock_scanner) as mock_cls:
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test"):
                pass

    call_kwargs = mock_cls.call_args.kwargs
    subscriptions = call_kwargs["subscriptions"]
    assert any("quote" in s for s in subscriptions)


async def test_mds_lifespan_with_default_settings_expect_daily_range_analyzer():
    from kuhl_haus.mdp.analyzers.daily_range_analyzer import DailyRangeAnalyzer
    mock_scanner = _make_mock_scanner()

    with patch(f"{MODULE}.MarketDataScanner", return_value=mock_scanner) as mock_cls:
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test"):
                pass

    call_kwargs = mock_cls.call_args.kwargs
    assert call_kwargs["analyzer_class"] is DailyRangeAnalyzer


# ---------------------------------------------------------------------------
# Lifespan — shutdown
# ---------------------------------------------------------------------------

async def test_mds_lifespan_shutdown_expect_scanner_stopped():
    mock_scanner = _make_mock_scanner()

    with patch(f"{MODULE}.MarketDataScanner", return_value=mock_scanner):
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test"):
                pass

    mock_scanner.stop.assert_awaited_once()


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

async def test_mds_health_with_scanner_running_expect_200(client):
    ac, _ = client
    response = await ac.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "OK"
    assert body["status_code"] == 1


async def test_mds_health_expect_service_name_market_data_scanner(client):
    ac, _ = client
    response = await ac.get("/health")
    assert response.json()["service"] == "Market Data Scanner"


async def test_mds_health_expect_scanner_stats_in_response(client):
    ac, mock_scanner = client
    mock_scanner.processed = 100
    mock_scanner.published_results = 95
    mock_scanner.errors = 2

    response = await ac.get("/health")
    body = response.json()
    assert "processed" in body
    assert "published_results" in body
    assert "errors" in body
    assert "mdc_connected" in body
    assert "running" in body


async def test_mds_health_expect_container_image_and_version(client):
    ac, _ = client
    response = await ac.get("/health")
    body = response.json()
    assert "container_image" in body
    assert "image_version" in body


async def test_mds_health_with_exception_expect_503(client):
    ac, mock_scanner = client
    # Simulate health check error by making mdc_connected raise
    type(mock_scanner).mdc_connected = property(lambda self: (_ for _ in ()).throw(RuntimeError("boom")))

    response = await ac.get("/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "ERROR"
    assert body["status_code"] == 0


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

async def test_mds_root_expect_redirect_to_health(client):
    ac, _ = client
    response = await ac.get("/", follow_redirects=False)
    assert response.status_code in (301, 302, 307, 308)
    assert "/health" in response.headers.get("location", "")
