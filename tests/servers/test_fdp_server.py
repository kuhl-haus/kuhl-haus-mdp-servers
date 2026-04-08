"""Unit tests for kuhl_haus.servers.fdp_server.

TDD red phase — fdp_server.py does not yet exist. These tests define the
expected contract and will fail at collection (ImportError) until the
implementation is added.

Run:
    pytest tests/servers/test_fdp_server.py -v
"""
import asyncio
import pytest
from asgi_lifespan import LifespanManager
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

MODULE = "kuhl_haus.servers.fdp_server"

from kuhl_haus.servers.fdp_server import app, settings  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_processor():
    mock = AsyncMock()
    mock.processed = 0
    mock.published = 0
    mock.error = 0
    mock.processing_error = 0
    mock.decoding_error = 0
    mock.mdq_connected = True
    mock.mdc_connected = True
    mock.start = AsyncMock()
    mock.stop = AsyncMock()
    return mock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def client():
    """AsyncClient with mocked FDP processor."""
    mock_processor = _make_mock_processor()

    with patch(f"{MODULE}.FinlightDataProcessor", return_value=mock_processor):
        async with LifespanManager(app):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as ac:
                yield ac, mock_processor


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

def test_fdp_settings_with_default_rabbitmq_url_expect_local_amqp():
    assert settings.rabbitmq_url == "amqp://mdq:mdq@localhost:5672/"


def test_fdp_settings_with_default_mdc_redis_url_expect_local_redis():
    assert settings.mdc_redis_url == "redis://mdc:mdc@localhost:6379/0"


def test_fdp_settings_with_default_wdc_redis_url_expect_local_redis():
    assert settings.wdc_redis_url == "redis://mdc:mdc@localhost:6379/1"


def test_fdp_settings_with_default_server_port_expect_4204():
    assert settings.server_port == 4204


def test_fdp_settings_with_default_log_level_expect_info():
    assert settings.log_level == "INFO"


def test_fdp_settings_with_default_prefetch_count():
    assert settings.prefetch_count == 100


def test_fdp_settings_with_default_max_concurrency():
    assert settings.max_concurrency == 500


def test_fdp_settings_with_default_queue_name_expect_news():
    assert settings.queue_name == "news"


# ---------------------------------------------------------------------------
# Lifespan — startup
# ---------------------------------------------------------------------------

async def test_fdp_lifespan_with_default_settings_expect_processor_started():
    # Arrange
    mock_processor = _make_mock_processor()

    with patch(f"{MODULE}.FinlightDataProcessor", return_value=mock_processor) as mock_cls:
        # Act
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test"):
                pass

    # Assert — processor instantiated and started
    mock_cls.assert_called_once()
    mock_processor.start.assert_awaited_once()


async def test_fdp_lifespan_with_default_settings_expect_queue_name_passed():
    # Arrange
    mock_processor = _make_mock_processor()

    with patch(f"{MODULE}.FinlightDataProcessor", return_value=mock_processor) as mock_cls:
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test"):
                pass

    # Assert — correct queue name passed to processor
    call_kwargs = mock_cls.call_args.kwargs
    assert call_kwargs["queue_name"] == settings.queue_name


async def test_fdp_lifespan_with_default_settings_expect_no_massive_api_key():
    # Arrange
    mock_processor = _make_mock_processor()

    with patch(f"{MODULE}.FinlightDataProcessor", return_value=mock_processor) as mock_cls:
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test"):
                pass

    # Assert — FinlightDataProcessor does not receive massive_api_key
    call_kwargs = mock_cls.call_args.kwargs
    assert "massive_api_key" not in call_kwargs


# ---------------------------------------------------------------------------
# Lifespan — shutdown
# ---------------------------------------------------------------------------

async def test_fdp_lifespan_shutdown_expect_processor_stopped():
    # Arrange
    mock_processor = _make_mock_processor()

    with patch(f"{MODULE}.FinlightDataProcessor", return_value=mock_processor):
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test"):
                pass

    # Assert — processor stopped on shutdown
    mock_processor.stop.assert_awaited_once()


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

async def test_fdp_health_with_processor_running_expect_200(client):
    # Arrange
    ac, _ = client

    # Act
    response = await ac.get("/health")

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "OK"
    assert body["status_code"] == 1


async def test_fdp_health_expect_service_name_finlight_data_processor(client):
    # Arrange
    ac, _ = client

    # Act
    response = await ac.get("/health")

    # Assert
    assert response.json()["service"] == "Finlight Data Processor"


async def test_fdp_health_expect_processor_stats_in_response(client):
    # Arrange
    ac, mock_processor = client
    mock_processor.processed = 42
    mock_processor.published = 38
    mock_processor.error = 1

    # Act
    response = await ac.get("/health")

    # Assert
    body = response.json()
    assert "processed" in body
    assert "published" in body
    assert "error" in body


async def test_fdp_health_expect_container_image_and_version(client):
    # Arrange
    ac, _ = client

    # Act
    response = await ac.get("/health")

    # Assert
    body = response.json()
    assert "container_image" in body
    assert "image_version" in body


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

async def test_fdp_root_expect_redirect_to_health(client):
    # Arrange
    ac, _ = client

    # Act
    response = await ac.get("/", follow_redirects=False)

    # Assert
    assert response.status_code in (301, 302, 307, 308)
    assert "/health" in response.headers.get("location", "")


# ---------------------------------------------------------------------------
# Parameterized settings
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("attr", [
    "rabbitmq_url",
    "mdc_redis_url",
    "wdc_redis_url",
    "prefetch_count",
    "max_concurrency",
    "queue_name",
    "log_level",
    "server_port",
    "container_image",
    "image_version",
])
def test_fdp_settings_with_attr_expect_exists(attr):
    # Arrange / Act / Assert
    assert hasattr(settings, attr)
