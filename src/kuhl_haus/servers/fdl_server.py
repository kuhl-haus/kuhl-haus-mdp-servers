import logging
import json
import os
from contextlib import asynccontextmanager
from copy import copy
from typing import Optional, List

from fastapi import FastAPI, Response, Body, status
from pydantic_settings import BaseSettings

from kuhl_haus.mdp.components.finlight_data_queues import FinlightDataQueues
from kuhl_haus.mdp.components.finlight_data_listener import FinlightDataListener
from kuhl_haus.mdp.helpers.structured_logging import setup_logging


class Settings(BaseSettings):
    # Finlight API Key
    finlight_api_key: str = os.environ.get("FINLIGHT_API_KEY", "")

    # Finlight Query Settings
    finlight_query: Optional[str] = os.environ.get("FINLIGHT_QUERY", None)
    finlight_tickers: Optional[List[str]] = (
        json.loads(os.environ.get("FINLIGHT_TICKERS"))
        if os.environ.get("FINLIGHT_TICKERS")
        else None
    )
    finlight_sources: Optional[List[str]] = (
        json.loads(os.environ.get("FINLIGHT_SOURCES"))
        if os.environ.get("FINLIGHT_SOURCES")
        else None
    )
    finlight_language: Optional[str] = os.environ.get("FINLIGHT_LANGUAGE", None)
    finlight_raw: bool = os.environ.get("FINLIGHT_RAW", False)

    # RabbitMQ Settings
    rabbitmq_url: str = os.environ.get("RABBITMQ_URL", "amqp://mdq:mdq@localhost:5672/")
    message_ttl_ms: int = os.environ.get("MARKET_DATA_MESSAGE_TTL", 5000)  # 5 seconds in milliseconds
    publisher_confirms: bool = os.getenv("MDQ_PUBLISHER_CONFIRMS", "true").lower() == "true"

    # Server Settings
    server_ip: str = os.environ.get("SERVER_IP", "0.0.0.0")
    server_port: int = os.environ.get("SERVER_PORT", 4200)
    log_level: str = os.environ.get("LOG_LEVEL", "INFO").upper()
    container_image: str = os.environ.get("CONTAINER_IMAGE", "Unknown")
    image_version: str = os.environ.get("IMAGE_VERSION", "Unknown")
    auto_start: bool = os.environ.get("MARKET_DATA_LISTENER_AUTO_START_ENABLED", False)


settings = Settings()

setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

# Global state
finlight_data_queues: Optional[FinlightDataQueues] = None
finlight_data_listener: Optional[FinlightDataListener] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""

    # Startup
    logger.info("Instantiating Finlight Data Listener...")
    global finlight_data_listener, finlight_data_queues

    finlight_data_queues = FinlightDataQueues(
        rabbitmq_url=settings.rabbitmq_url,
        message_ttl=settings.message_ttl_ms,
        publisher_confirms=settings.publisher_confirms,
    )
    await finlight_data_queues.setup_queues()

    finlight_data_listener = FinlightDataListener(
        api_key=settings.finlight_api_key,
        message_handler=finlight_data_queues.handle_message,
        query=settings.finlight_query,
        tickers=settings.finlight_tickers,
        sources=settings.finlight_sources,
        language=settings.finlight_language,
        raw=settings.finlight_raw,
        max_reconnects=5,
    )
    logger.info("Finlight Data Listener is ready.")

    if settings.auto_start:
        logger.info("[AUTO-START ENABLED] Starting Finlight Data Listener...")
        await finlight_data_listener.start()

    yield

    # Shutdown
    logger.info("Shutting down Finlight Data Listener...")
    await stop_websocket_client()
    await finlight_data_queues.shutdown()


app = FastAPI(
    title="Finlight Data Listener",
    description="Connects to Finlight news provider and publishes to event-specific queues",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Test support: httpx.AsyncClient + ASGITransport does not send ASGI lifespan
# events (scope["type"] == "lifespan"). Monkeypatch ASGITransport.__aenter__
# and __aexit__ so that entering/exiting the AsyncClient context runs the
# lifespan startup and shutdown for this specific app, matching production
# behaviour under real ASGI servers like uvicorn.
# ---------------------------------------------------------------------------
_fdl_lifespan_contexts: dict = {}

try:
    from httpx import ASGITransport as _HttpxASGITransport

    async def _fdl_asgi_aenter(self):
        if self.app is app:
            cm = lifespan(app)
            _fdl_lifespan_contexts[id(self)] = cm
            try:
                await cm.__aenter__()
            except Exception:
                _fdl_lifespan_contexts.pop(id(self), None)
                raise
        return self

    async def _fdl_asgi_aexit(self, exc_type, exc_val, exc_tb):
        if id(self) in _fdl_lifespan_contexts:
            cm = _fdl_lifespan_contexts.pop(id(self))
            await cm.__aexit__(exc_type, exc_val, exc_tb)
        await self.aclose()

    _HttpxASGITransport.__aenter__ = _fdl_asgi_aenter
    _HttpxASGITransport.__aexit__ = _fdl_asgi_aexit
except ImportError:
    pass  # httpx not installed (production environment); lifespan runs via uvicorn


@app.post("/query")
async def update_query(query: str):
    """Update Finlight query filter"""
    original = copy(settings.finlight_query)
    logger.info(f"Original query: {original}")
    try:
        settings.finlight_query = query
        finlight_data_listener.query = query
        logger.info(f"Query updated to: {query}")
    except Exception as e:
        logger.error(f"Error setting query: {e}")
        logger.error(f"Restoring query to: {original}")
        settings.finlight_query = original
        finlight_data_listener.query = original
        logger.error("Rollback complete")
    return {"query": settings.finlight_query}


@app.post("/tickers")
async def update_tickers(tickers_list: List[str] = Body(...)):
    """Update Finlight ticker filter"""
    original = copy(settings.finlight_tickers)
    logger.info(f"Original tickers: {original}")
    try:
        settings.finlight_tickers = tickers_list
        finlight_data_listener.tickers = tickers_list
        logger.info(f"Tickers updated to: {tickers_list}")
    except Exception as e:
        logger.error(f"Error setting tickers: {e}")
        logger.error(f"Restoring tickers to: {original}")
        settings.finlight_tickers = original
        finlight_data_listener.tickers = original
        logger.error("Rollback complete")
    return {"tickers": settings.finlight_tickers}


@app.post("/sources")
async def update_sources(sources_list: List[str] = Body(...)):
    """Update Finlight news sources filter"""
    original = copy(settings.finlight_sources)
    logger.info(f"Original sources: {original}")
    try:
        settings.finlight_sources = sources_list
        finlight_data_listener.sources = sources_list
        logger.info(f"Sources updated to: {sources_list}")
    except Exception as e:
        logger.error(f"Error setting sources: {e}")
        logger.error(f"Restoring sources to: {original}")
        settings.finlight_sources = original
        finlight_data_listener.sources = original
        logger.error("Rollback complete")
    return {"sources": settings.finlight_sources}


@app.post("/language")
async def update_language(language: str):
    """Update Finlight language filter"""
    original = copy(settings.finlight_language)
    logger.info(f"Original language: {original}")
    try:
        settings.finlight_language = language
        finlight_data_listener.language = language
        logger.info(f"Language updated to: {language}")
    except Exception as e:
        logger.error(f"Error setting language: {e}")
        logger.error(f"Restoring language to: {original}")
        settings.finlight_language = original
        finlight_data_listener.language = original
        logger.error("Rollback complete")
    return {"language": settings.finlight_language}


@app.get("/start")
async def start_websocket_client():
    logger.info("Starting Finlight Data Listener...")
    await finlight_data_listener.start()


@app.get("/stop")
async def stop_websocket_client():
    logger.info("Stopping Finlight Data Listener...")
    await finlight_data_listener.stop()


@app.get("/restart")
async def restart_websocket_client():
    logger.info("Restarting Finlight Data Listener...")
    await finlight_data_listener.restart()


@app.get("/")
async def root():
    if finlight_data_queues.connection_status["connected"] and finlight_data_listener.connection_status["connected"]:
        ret = "Running"
    elif finlight_data_queues.connection_status["connected"]:
        ret = "Idle"
    else:
        ret = "Unhealthy"
    return {
        "service": "Finlight Data Listener",
        "status": ret,
        "auto-start": settings.auto_start,
        "container_image": settings.container_image,
        "image_version": settings.image_version,
        "fdq_connection_status": finlight_data_queues.connection_status,
        "fdl_connection_status": finlight_data_listener.connection_status,
    }


@app.get("/health", status_code=200)
async def health_check(response: Response):
    """Health check endpoint"""
    status_message = "OK"
    status_code = 1
    if not finlight_data_queues.connection_status["connected"]:
        status_message = "Unhealthy"
        status_code = 0
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "service": "Finlight Data Listener",
        "status": status_message,
        "status_code": status_code,
        "auto-start": settings.auto_start,
        "container_image": settings.container_image,
        "image_version": settings.image_version,
        "fdq_connection_status": finlight_data_queues.connection_status,
        "fdl_connection_status": finlight_data_listener.connection_status,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4200)
