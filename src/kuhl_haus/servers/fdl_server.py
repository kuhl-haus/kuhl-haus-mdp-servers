"""FDL server — Finlight Data Listener.

Composes FinlightDataQueues + FinlightSimpleListener to stream real-time
news articles from the Finlight WebSocket API to RabbitMQ.

Uses FinlightSimpleListener which mirrors the verified working Finlight SDK
pattern: sync on_article callback with takeover=True and includeEntities=True.
"""
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, Response, status
from pydantic_settings import BaseSettings

from kuhl_haus.mdp.components.finlight_data_queues import FinlightDataQueues
from kuhl_haus.mdp.components.finlight_simple_listener import FinlightSimpleListener
from kuhl_haus.mdp.helpers.structured_logging import setup_logging


class Settings(BaseSettings):
    # Finlight API Key
    finlight_api_key: str = os.environ.get("FINLIGHT_API_KEY", "")

    # Finlight filter settings
    finlight_query: Optional[str] = os.environ.get("FINLIGHT_QUERY", None)
    finlight_tickers: Optional[List[str]] = (
        json.loads(os.environ.get("FINLIGHT_TICKERS", "null"))
        if os.environ.get("FINLIGHT_TICKERS")
        else None
    )
    finlight_sources: Optional[List[str]] = (
        json.loads(os.environ.get("FINLIGHT_SOURCES", "null"))
        if os.environ.get("FINLIGHT_SOURCES")
        else None
    )
    finlight_language: Optional[str] = os.environ.get("FINLIGHT_LANGUAGE", None)
    finlight_raw: bool = os.environ.get("FINLIGHT_RAW", False)
    finlight_include_entities: bool = os.environ.get("FINLIGHT_INCLUDE_ENTITIES", True)

    # RabbitMQ Settings
    rabbitmq_url: str = os.environ.get("RABBITMQ_URL", "amqp://mdq:mdq@localhost:5672/")
    message_ttl_ms: int = os.environ.get("MARKET_DATA_MESSAGE_TTL", 5000)
    publisher_confirms: bool = os.getenv("MDQ_PUBLISHER_CONFIRMS", "true").lower() == "true"

    # Server Settings
    server_ip: str = os.environ.get("SERVER_IP", "0.0.0.0")
    server_port: int = os.environ.get("SERVER_PORT", 4203)
    log_level: str = os.environ.get("LOG_LEVEL", "INFO").upper()
    container_image: str = os.environ.get("CONTAINER_IMAGE", "Unknown")
    image_version: str = os.environ.get("IMAGE_VERSION", "Unknown")
    auto_start: bool = os.environ.get("MARKET_DATA_LISTENER_AUTO_START_ENABLED", False)


settings = Settings()

setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

# Global state
finlight_data_queues: Optional[FinlightDataQueues] = None
finlight_listener: Optional[FinlightSimpleListener] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global finlight_listener, finlight_data_queues

    logger.info("Instantiating Finlight Data Listener...")

    finlight_data_queues = FinlightDataQueues(
        rabbitmq_url=settings.rabbitmq_url,
        message_ttl=settings.message_ttl_ms,
        publisher_confirms=settings.publisher_confirms,
    )
    await finlight_data_queues.setup_queues()

    finlight_listener = FinlightSimpleListener(
        api_key=settings.finlight_api_key,
        queues=finlight_data_queues,
        query=settings.finlight_query,
        tickers=settings.finlight_tickers,
        sources=settings.finlight_sources,
        language=settings.finlight_language,
        raw=settings.finlight_raw,
        include_entities=settings.finlight_include_entities,
    )
    logger.info("Finlight Data Listener is ready.")

    if settings.auto_start:
        logger.info("[AUTO-START ENABLED] Starting Finlight Data Listener...")
        await finlight_listener.start()

    yield

    # Shutdown
    logger.info("Shutting down Finlight Data Listener...")
    if finlight_listener:
        await finlight_listener.stop()
    if finlight_data_queues:
        await finlight_data_queues.shutdown()


app = FastAPI(
    title="Finlight Data Listener",
    description="Connects to Finlight news stream and publishes articles to RabbitMQ queue",
    lifespan=lifespan,
)


@app.get("/start")
async def start_listener():
    logger.info("Starting Finlight Data Listener...")
    await finlight_listener.start()


@app.get("/stop")
async def stop_listener():
    logger.info("Stopping Finlight Data Listener...")
    await finlight_listener.stop()


@app.get("/restart")
async def restart_listener():
    logger.info("Restarting Finlight Data Listener...")
    await finlight_listener.stop()
    await finlight_listener.start()


@app.get("/")
async def root():
    fdq_connected = finlight_data_queues.connection_status["connected"]
    fdl_connected = finlight_listener.connection_status["connected"]
    if fdq_connected and fdl_connected:
        ret = "Running"
    elif fdq_connected:
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
        "fdl_connection_status": finlight_listener.connection_status,
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
        "fdl_connection_status": finlight_listener.connection_status,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4203)
