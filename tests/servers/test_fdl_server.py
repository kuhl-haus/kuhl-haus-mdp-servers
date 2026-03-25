"""Unit tests for kuhl_haus.servers.fdl_server."""
import pytest
from asgi_lifespan import LifespanManager
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

MODULE = "kuhl_haus.servers.fdl_server"

from kuhl_haus.servers.fdl_server import app, settings  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_fdq(connected: bool = True) -> AsyncMock:
    mock = AsyncMock()
    mock.connection_status = {
        "connected": connected,
        "last_message_time": None,
        "messages_received": 0,
        "news": 0,
        "reconnect_attempts": 0,
    }
    mock.setup_queues = AsyncMock()
    mock.shutdown = AsyncMock()
    mock.handle_message = AsyncMock()
    return mock


def _make_mock_listener(connected: bool = False) -> MagicMock:
    mock = MagicMock()
    mock.connection_status = {
        "connected": connected,
        "healthy": connected,
        "articles_received": 0,
        "errors": 0,
    }
    mock.start = AsyncMock()
    mock.stop = AsyncMock()
    return mock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def client():
    """AsyncClient with FDQ connected and listener idle."""
    mock_fdq = _make_mock_fdq(connected=True)
    mock_listener = _make_mock_listener(connected=False)

    with patch(f"{MODULE}.FinlightDataQueues", return_value=mock_fdq), \
         patch(f"{MODULE}.FinlightSimpleListener", return_value=mock_listener):
        async with LifespanManager(app):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as ac:
                yield ac, mock_fdq, mock_listener


@pytest.fixture
async def client_both_connected():
    mock_fdq = _make_mock_fdq(connected=True)
    mock_listener = _make_mock_listener(connected=True)

    with patch(f"{MODULE}.FinlightDataQueues", return_value=mock_fdq), \
         patch(f"{MODULE}.FinlightSimpleListener", return_value=mock_listener):
        async with LifespanManager(app):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as ac:
                yield ac, mock_fdq, mock_listener


@pytest.fixture
async def client_fdq_disconnected():
    mock_fdq = _make_mock_fdq(connected=False)
    mock_listener = _make_mock_listener(connected=False)

    with patch(f"{MODULE}.FinlightDataQueues", return_value=mock_fdq), \
         patch(f"{MODULE}.FinlightSimpleListener", return_value=mock_listener):
        async with LifespanManager(app):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as ac:
                yield ac, mock_fdq, mock_listener


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

def test_fdl_settings_with_default_rabbitmq_url_expect_local_amqp():
    assert settings.rabbitmq_url == "amqp://mdq:mdq@localhost:5672/"


def test_fdl_settings_with_default_message_ttl_expect_5000():
    assert settings.message_ttl_ms == 5000


def test_fdl_settings_with_default_auto_start_expect_false():
    assert settings.auto_start is False


def test_fdl_settings_with_default_log_level_expect_info():
    assert settings.log_level == "INFO"


def test_fdl_settings_with_default_raw_expect_false():
    assert settings.finlight_raw is False


def test_fdl_settings_with_default_query_expect_none():
    assert settings.finlight_query is None


def test_fdl_settings_with_default_tickers_expect_none():
    assert settings.finlight_tickers is None


def test_fdl_settings_with_default_sources_expect_none():
    assert settings.finlight_sources is None


def test_fdl_settings_with_default_language_expect_none():
    assert settings.finlight_language is None


def test_fdl_settings_with_finlight_api_key_attribute_expect_exists():
    assert hasattr(settings, "finlight_api_key")


def test_fdl_settings_with_default_publisher_confirms_expect_true():
    assert settings.publisher_confirms is True


def test_fdl_settings_with_default_server_port_expect_4203():
    assert settings.server_port == 4203


def test_fdl_settings_with_include_entities_expect_true():
    assert settings.finlight_include_entities is True


# ---------------------------------------------------------------------------
# Lifespan — startup
# ---------------------------------------------------------------------------

async def test_fdl_lifespan_with_default_settings_expect_fdq_created_and_setup():
    # Arrange
    mock_fdq = _make_mock_fdq()
    mock_listener = _make_mock_listener()

    with patch(f"{MODULE}.FinlightDataQueues", return_value=mock_fdq) as mock_fdq_cls, \
         patch(f"{MODULE}.FinlightSimpleListener", return_value=mock_listener):
        # Act
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test"):
                pass

    # Assert
    mock_fdq_cls.assert_called_once()
    mock_fdq.setup_queues.assert_awaited_once()


async def test_fdl_lifespan_with_default_settings_expect_listener_created_with_queues():
    # Arrange
    mock_fdq = _make_mock_fdq()
    mock_listener = _make_mock_listener()

    with patch(f"{MODULE}.FinlightDataQueues", return_value=mock_fdq), \
         patch(f"{MODULE}.FinlightSimpleListener", return_value=mock_listener) as mock_cls:
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test"):
                pass

    # Assert — listener instantiated with queues instance
    mock_cls.assert_called_once()
    call_kwargs = mock_cls.call_args.kwargs
    assert call_kwargs["queues"] is mock_fdq


async def test_fdl_lifespan_with_default_settings_expect_include_entities_true():
    # Arrange
    mock_fdq = _make_mock_fdq()
    mock_listener = _make_mock_listener()

    with patch(f"{MODULE}.FinlightDataQueues", return_value=mock_fdq), \
         patch(f"{MODULE}.FinlightSimpleListener", return_value=mock_listener) as mock_cls:
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test"):
                pass

    call_kwargs = mock_cls.call_args.kwargs
    assert call_kwargs["include_entities"] is True


async def test_fdl_lifespan_with_auto_start_disabled_expect_listener_start_not_called():
    # Arrange
    mock_fdq = _make_mock_fdq()
    mock_listener = _make_mock_listener()

    with patch(f"{MODULE}.FinlightDataQueues", return_value=mock_fdq), \
         patch(f"{MODULE}.FinlightSimpleListener", return_value=mock_listener), \
         patch.object(settings, "auto_start", False):
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test"):
                pass

    # Assert
    mock_listener.start.assert_not_awaited()


async def test_fdl_lifespan_with_auto_start_enabled_expect_listener_start_called():
    # Arrange
    mock_fdq = _make_mock_fdq()
    mock_listener = _make_mock_listener()

    with patch(f"{MODULE}.FinlightDataQueues", return_value=mock_fdq), \
         patch(f"{MODULE}.FinlightSimpleListener", return_value=mock_listener), \
         patch.object(settings, "auto_start", True):
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test"):
                pass

    # Assert
    mock_listener.start.assert_awaited_once()


# ---------------------------------------------------------------------------
# Lifespan — shutdown
# ---------------------------------------------------------------------------

async def test_fdl_lifespan_shutdown_expect_listener_stop_and_fdq_shutdown():
    # Arrange
    mock_fdq = _make_mock_fdq()
    mock_listener = _make_mock_listener()

    with patch(f"{MODULE}.FinlightDataQueues", return_value=mock_fdq), \
         patch(f"{MODULE}.FinlightSimpleListener", return_value=mock_listener):
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test"):
                pass

    # Assert
    mock_listener.stop.assert_awaited()
    mock_fdq.shutdown.assert_awaited_once()


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

async def test_fdl_root_with_both_connected_expect_running_status(client_both_connected):
    # Arrange
    ac, _, _ = client_both_connected

    # Act
    response = await ac.get("/")

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "Running"


async def test_fdl_root_with_only_fdq_connected_expect_idle_status(client):
    # Arrange
    ac, _, _ = client

    # Act
    response = await ac.get("/")

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "Idle"


async def test_fdl_root_with_fdq_disconnected_expect_unhealthy_status(client_fdq_disconnected):
    # Arrange
    ac, _, _ = client_fdq_disconnected

    # Act
    response = await ac.get("/")

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "Unhealthy"


async def test_fdl_root_expect_service_name_and_connection_fields(client):
    # Arrange
    ac, _, _ = client

    # Act
    response = await ac.get("/")

    # Assert
    body = response.json()
    assert body["service"] == "Finlight Data Listener"
    assert "fdq_connection_status" in body
    assert "fdl_connection_status" in body


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

async def test_fdl_health_with_fdq_connected_expect_200_ok(client):
    # Arrange
    ac, _, _ = client

    # Act
    response = await ac.get("/health")

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "OK"
    assert body["status_code"] == 1


async def test_fdl_health_with_fdq_disconnected_expect_503_unhealthy(client_fdq_disconnected):
    # Arrange
    ac, _, _ = client_fdq_disconnected

    # Act
    response = await ac.get("/health")

    # Assert
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "Unhealthy"
    assert body["status_code"] == 0


async def test_fdl_health_expect_service_name_in_response(client):
    # Arrange
    ac, _, _ = client

    # Act
    response = await ac.get("/health")

    # Assert
    assert response.json()["service"] == "Finlight Data Listener"


# ---------------------------------------------------------------------------
# GET /start /stop /restart
# ---------------------------------------------------------------------------

async def test_fdl_start_with_stopped_listener_expect_start_called(client):
    # Arrange
    ac, _, mock_listener = client

    # Act
    response = await ac.get("/start")

    # Assert
    assert response.status_code == 200
    mock_listener.start.assert_awaited_once()


async def test_fdl_stop_with_listener_expect_stop_called(client):
    # Arrange
    ac, _, mock_listener = client

    # Act
    response = await ac.get("/stop")

    # Assert
    assert response.status_code == 200
    mock_listener.stop.assert_awaited_once()


async def test_fdl_restart_with_listener_expect_stop_then_start(client):
    # Arrange
    ac, _, mock_listener = client

    # Act
    response = await ac.get("/restart")

    # Assert
    assert response.status_code == 200
    mock_listener.stop.assert_awaited_once()
    mock_listener.start.assert_awaited_once()


# ---------------------------------------------------------------------------
# Parameterized settings attributes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("attr", [
    "rabbitmq_url",
    "redis_url" if hasattr(settings, "redis_url") else "rabbitmq_url",
    "finlight_api_key",
    "finlight_query",
    "finlight_tickers",
    "finlight_sources",
    "finlight_language",
    "finlight_raw",
    "finlight_include_entities",
    "server_port",
    "log_level",
    "container_image",
    "image_version",
    "auto_start",
])
def test_fdl_settings_with_attr_expect_exists(attr):
    # Arrange / Act / Assert
    assert hasattr(settings, attr)
