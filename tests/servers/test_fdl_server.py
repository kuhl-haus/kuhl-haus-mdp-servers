"""Unit tests for kuhl_haus.servers.fdl_server.

TDD red phase — fdl_server.py does not yet exist. These tests define the
expected contract and will fail at collection (ImportError) until the
implementation is added.

Run:
    pytest tests/servers/test_fdl_server.py -v
"""
import pytest
from asgi_lifespan import LifespanManager
from copy import copy
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from httpx import AsyncClient, ASGITransport

MODULE = "kuhl_haus.servers.fdl_server"

# This import drives the red phase — will raise ImportError until implemented.
from kuhl_haus.servers.fdl_server import app, settings  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_fdq(connected: bool = True) -> AsyncMock:
    """Return an AsyncMock standing in for FinlightDataQueues."""
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
    """Return a MagicMock standing in for FinlightDataListener."""
    mock = MagicMock()
    mock.connection_status = {
        "connected": connected,
        "healthy": connected,
        "language": None,
        "query": None,
        "reconnects": 0,
        "sources": None,
        "tickers": None,
    }
    mock.start = AsyncMock()
    mock.stop = AsyncMock()
    mock.restart = AsyncMock()
    return mock


def _make_raising_listener() -> object:
    """Return a listener-like object whose property setters raise on the first
    call (simulating a transient error) and succeed on the second call
    (simulating a successful rollback assignment).

    Each attribute (query, tickers, sources, language) tracks its own
    call count so rollback tests for different properties are independent.
    """

    class _RaisingOnFirstSetListener:
        def __init__(self):
            self._call_counts: dict = {}
            self.connection_status = {
                "connected": False,
                "healthy": False,
                "language": None,
                "query": None,
                "reconnects": 0,
                "sources": None,
                "tickers": None,
            }
            self.start = AsyncMock()
            self.stop = AsyncMock()
            self.restart = AsyncMock()

        def _raise_once(self, attr: str) -> None:
            n = self._call_counts.get(attr, 0) + 1
            self._call_counts[attr] = n
            if n == 1:
                raise RuntimeError(f"simulated error setting {attr}")

        @property
        def query(self):
            return None

        @query.setter
        def query(self, value):
            self._raise_once("query")

        @property
        def tickers(self):
            return None

        @tickers.setter
        def tickers(self, value):
            self._raise_once("tickers")

        @property
        def sources(self):
            return None

        @sources.setter
        def sources(self, value):
            self._raise_once("sources")

        @property
        def language(self):
            return None

        @language.setter
        def language(self, value):
            self._raise_once("language")

    return _RaisingOnFirstSetListener()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def client():
    """AsyncClient with FDQ connected and listener idle (not connected).

    LifespanManager triggers FastAPI lifespan; mocked components prevent real I/O.
    """
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
    """AsyncClient where both FDQ and FDL report connected=True."""
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
    """AsyncClient where FDQ reports connected=False."""
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
# Settings defaults
# ---------------------------------------------------------------------------

def test_fdl_settings_with_default_rabbitmq_url_expect_local_amqp():
    # Arrange / Act — settings is instantiated at module load time
    # Assert
    assert settings.rabbitmq_url == "amqp://mdq:mdq@localhost:5672/"


def test_fdl_settings_with_default_message_ttl_expect_900000():
    assert settings.message_ttl_ms == 900000


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


def test_fdl_settings_with_default_language_expect_en():
    assert settings.finlight_language == "en"


def test_fdl_settings_with_finlight_api_key_attribute_expect_exists():
    assert hasattr(settings, "finlight_api_key")


def test_fdl_settings_with_default_publisher_confirms_expect_true():
    assert settings.publisher_confirms is True


def test_fdl_settings_with_default_listener_class_expect_finlight_simple_listener():
    assert settings.finlight_data_listener_class == "FinlightSimpleListener"


# ---------------------------------------------------------------------------
# Lifespan — startup
# ---------------------------------------------------------------------------

async def test_fdl_lifespan_with_default_settings_expect_fdq_created_and_setup():
    # Arrange
    mock_fdq = _make_mock_fdq()
    mock_listener = _make_mock_listener()

    with patch(f"{MODULE}.FinlightDataQueues", return_value=mock_fdq) as mock_fdq_cls, \
         patch(f"{MODULE}.FinlightDataListener", return_value=mock_listener):
        # Act — AsyncClient context entry triggers lifespan startup
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test"):
                pass

    # Assert
    mock_fdq_cls.assert_called_once()
    mock_fdq.setup_queues.assert_awaited_once()


async def test_fdl_lifespan_with_default_settings_expect_fdl_created_with_queues():
    # Arrange
    mock_fdq = _make_mock_fdq()
    mock_listener = _make_mock_listener()

    with patch(f"{MODULE}.FinlightDataQueues", return_value=mock_fdq), \
         patch(f"{MODULE}.FinlightSimpleListener", return_value=mock_listener) as mock_fdl_cls:
        # Act
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test"):
                pass

    # Assert — listener instantiated with queues
    mock_fdl_cls.assert_called_once()
    call_kwargs = mock_fdl_cls.call_args.kwargs
    assert call_kwargs["queues"] == mock_fdq


async def test_fdl_lifespan_with_auto_start_disabled_expect_listener_start_not_called():
    # Arrange
    mock_fdq = _make_mock_fdq()
    mock_listener = _make_mock_listener()

    with patch(f"{MODULE}.FinlightDataQueues", return_value=mock_fdq), \
         patch(f"{MODULE}.FinlightSimpleListener", return_value=mock_listener), \
         patch.object(settings, "auto_start", False):
        # Act
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
        # Act
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test"):
                pass

    # Assert
    mock_listener.start.assert_awaited_once()


async def test_fdl_lifespan_with_finlight_data_listener_class_expect_instantiated_with_filters():
    # Arrange
    mock_fdq = _make_mock_fdq()
    mock_listener = _make_mock_listener()

    with patch(f"{MODULE}.FinlightDataQueues", return_value=mock_fdq), \
         patch(f"{MODULE}.FinlightDataListener", return_value=mock_listener) as mock_fdl_cls, \
         patch.object(settings, "finlight_data_listener_class", "FinlightDataListener"):
        # Act
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test"):
                pass

    # Assert — FinlightDataListener instantiated with filter parameters
    mock_fdl_cls.assert_called_once()
    call_kwargs = mock_fdl_cls.call_args.kwargs
    assert call_kwargs["queues"] == mock_fdq
    assert "query" in call_kwargs
    assert "tickers" in call_kwargs
    assert "sources" in call_kwargs
    assert "language" in call_kwargs
    assert "max_reconnects" in call_kwargs


async def test_fdl_lifespan_with_invalid_listener_class_expect_value_error():
    # Arrange
    mock_fdq = _make_mock_fdq()

    with patch(f"{MODULE}.FinlightDataQueues", return_value=mock_fdq), \
         patch.object(settings, "finlight_data_listener_class", "InvalidListener"):
        # Act & Assert
        with pytest.raises(ValueError, match="Unknown listener class: InvalidListener"):
            async with LifespanManager(app):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test"):
                    pass


# ---------------------------------------------------------------------------
# Lifespan — shutdown
# ---------------------------------------------------------------------------

async def test_fdl_lifespan_shutdown_expect_listener_stop_and_fdq_shutdown_called():
    # Arrange
    mock_fdq = _make_mock_fdq()
    mock_listener = _make_mock_listener()

    with patch(f"{MODULE}.FinlightDataQueues", return_value=mock_fdq), \
         patch(f"{MODULE}.FinlightSimpleListener", return_value=mock_listener):
        # Act — context exit triggers lifespan shutdown
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test"):
                pass

    # Assert — stop (from stop_websocket_client helper) and shutdown both called
    mock_listener.stop.assert_awaited()
    mock_fdq.shutdown.assert_awaited_once()


# ---------------------------------------------------------------------------
# GET /  — status endpoint
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
    # Arrange — client fixture: fdq connected, listener not connected
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
    assert "auto-start" in body
    assert "container_image" in body
    assert "image_version" in body


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
# GET /start  /stop  /restart
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


async def test_fdl_restart_with_listener_expect_restart_called(client):
    # Arrange
    ac, _, mock_listener = client

    # Act
    response = await ac.get("/restart")

    # Assert
    assert response.status_code == 200
    mock_listener.restart.assert_awaited_once()


# ---------------------------------------------------------------------------
# POST /query
# ---------------------------------------------------------------------------

async def test_fdl_query_with_valid_string_expect_settings_and_listener_updated(client):
    # Arrange
    ac, _, mock_listener = client
    new_query = "Tesla earnings"
    saved = settings.finlight_query

    try:
        # Act
        response = await ac.post("/query", params={"query": new_query})

        # Assert
        assert response.status_code == 200
        assert settings.finlight_query == new_query
        assert mock_listener.query == new_query
    finally:
        settings.finlight_query = saved


async def test_fdl_query_with_listener_error_expect_settings_rolled_back():
    # Arrange
    mock_fdq = _make_mock_fdq()
    raising_listener = _make_raising_listener()
    saved = settings.finlight_query

    with patch(f"{MODULE}.FinlightDataQueues", return_value=mock_fdq), \
         patch(f"{MODULE}.FinlightSimpleListener", return_value=raising_listener):
        async with LifespanManager(app):
         async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            try:
                # Act — listener.query setter raises on first call; rollback on second
                response = await ac.post("/query", params={"query": "Tesla"})

                # Assert — endpoint handles error gracefully; settings rolled back
                assert response.status_code == 200
                assert settings.finlight_query == saved
            finally:
                settings.finlight_query = saved


# ---------------------------------------------------------------------------
# POST /tickers
# ---------------------------------------------------------------------------

async def test_fdl_tickers_with_valid_list_expect_settings_and_listener_updated(client):
    # Arrange
    ac, _, mock_listener = client
    new_tickers = ["AAPL", "TSLA", "NVDA"]
    saved = copy(settings.finlight_tickers)

    try:
        # Act
        response = await ac.post("/tickers", json=new_tickers)

        # Assert
        assert response.status_code == 200
        assert settings.finlight_tickers == new_tickers
        assert mock_listener.tickers == new_tickers
    finally:
        settings.finlight_tickers = saved


async def test_fdl_tickers_with_listener_error_expect_settings_rolled_back():
    # Arrange
    mock_fdq = _make_mock_fdq()
    raising_listener = _make_raising_listener()
    saved = copy(settings.finlight_tickers)

    with patch(f"{MODULE}.FinlightDataQueues", return_value=mock_fdq), \
         patch(f"{MODULE}.FinlightSimpleListener", return_value=raising_listener):
        async with LifespanManager(app):
         async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            try:
                # Act
                response = await ac.post("/tickers", json=["AAPL"])

                # Assert
                assert response.status_code == 200
                assert settings.finlight_tickers == saved
            finally:
                settings.finlight_tickers = saved


# ---------------------------------------------------------------------------
# POST /sources
# ---------------------------------------------------------------------------

async def test_fdl_sources_with_valid_list_expect_settings_and_listener_updated(client):
    # Arrange
    ac, _, mock_listener = client
    new_sources = ["reuters", "bloomberg"]
    saved = copy(settings.finlight_sources)

    try:
        # Act
        response = await ac.post("/sources", json=new_sources)

        # Assert
        assert response.status_code == 200
        assert settings.finlight_sources == new_sources
        assert mock_listener.sources == new_sources
    finally:
        settings.finlight_sources = saved


async def test_fdl_sources_with_listener_error_expect_settings_rolled_back():
    # Arrange
    mock_fdq = _make_mock_fdq()
    raising_listener = _make_raising_listener()
    saved = copy(settings.finlight_sources)

    with patch(f"{MODULE}.FinlightDataQueues", return_value=mock_fdq), \
         patch(f"{MODULE}.FinlightSimpleListener", return_value=raising_listener):
        async with LifespanManager(app):
         async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            try:
                # Act
                response = await ac.post("/sources", json=["reuters"])

                # Assert
                assert response.status_code == 200
                assert settings.finlight_sources == saved
            finally:
                settings.finlight_sources = saved


# ---------------------------------------------------------------------------
# POST /language
# ---------------------------------------------------------------------------

async def test_fdl_language_with_valid_string_expect_settings_and_listener_updated(client):
    # Arrange
    ac, _, mock_listener = client
    new_language = "en"
    saved = settings.finlight_language

    try:
        # Act
        response = await ac.post("/language", params={"language": new_language})

        # Assert
        assert response.status_code == 200
        assert settings.finlight_language == new_language
        assert mock_listener.language == new_language
    finally:
        settings.finlight_language = saved


async def test_fdl_language_with_listener_error_expect_settings_rolled_back():
    # Arrange
    mock_fdq = _make_mock_fdq()
    raising_listener = _make_raising_listener()
    saved = settings.finlight_language

    with patch(f"{MODULE}.FinlightDataQueues", return_value=mock_fdq), \
         patch(f"{MODULE}.FinlightSimpleListener", return_value=raising_listener):
        async with LifespanManager(app):
         async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            try:
                # Act
                response = await ac.post("/language", params={"language": "xx"})

                # Assert
                assert response.status_code == 200
                assert settings.finlight_language == saved
            finally:
                settings.finlight_language = saved
