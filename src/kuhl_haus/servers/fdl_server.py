import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from copy import copy
from typing import Optional, List, Union, Any, Dict

from fastapi import FastAPI, Response, status
from pydantic_settings import BaseSettings

from kuhl_haus.mdp.components.finlight_data_queues import FinlightDataQueues
from kuhl_haus.mdp.components.finlight_data_listener import FinlightDataListener
from kuhl_haus.mdp.components.finlight_simple_listener import FinlightSimpleListener
from kuhl_haus.mdp.helpers.structured_logging import setup_logging


class Settings(BaseSettings):
    # Finlight Data Listener Settings
    finlight_data_listener_class: str = os.environ.get(
        "FINLIGHT_DATA_LISTENER_CLASS", "FinlightSimpleListener"
    )

    # Finlight API Key
    finlight_api_key: str = os.environ.get("FINLIGHT_API_KEY", "")

    # Finlight filter settings
    finlight_query: Optional[str] = os.environ.get("FINLIGHT_QUERY", None)
    finlight_tickers: Optional[List[str]] = (
        json.loads(os.environ.get("FINLIGHT_TICKERS", "*"))
        if os.environ.get("FINLIGHT_TICKERS")
        else None
    )
    finlight_sources: Optional[List[str]] = (
        json.loads(os.environ.get("FINLIGHT_SOURCES", "*"))
        if os.environ.get("FINLIGHT_SOURCES")
        else None
    )
    finlight_language: Optional[str] = os.environ.get("FINLIGHT_LANGUAGE", "en")
    finlight_raw: bool = os.environ.get("FINLIGHT_RAW", False)
    max_reconnects: Optional[int] = os.environ.get("FINLIGHT_MAX_RECONNECTS", 5)

    # RabbitMQ Settings
    rabbitmq_url: str = os.environ.get("RABBITMQ_URL", "amqp://mdq:mdq@localhost:5672/")
    message_ttl_ms: int = os.environ.get("MARKET_DATA_MESSAGE_TTL", 900000)
    publisher_confirms: bool = os.getenv("MDQ_PUBLISHER_CONFIRMS", "true").lower() == "true"

    # Server Settings
    server_ip: str = os.environ.get("SERVER_IP", "0.0.0.0")
    server_port: int = os.environ.get("SERVER_PORT", 4203)
    log_level: str = os.environ.get("LOG_LEVEL", "INFO").upper()
    container_image: str = os.environ.get("CONTAINER_IMAGE", "Unknown")
    image_version: str = os.environ.get("IMAGE_VERSION", "Unknown")
    auto_start: bool = os.environ.get("FDL_AUTO_START_ENABLED", False)


settings = Settings()

setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

# Global state
fdq: Optional[FinlightDataQueues] = None
fdl: Optional[Union[FinlightDataListener, FinlightSimpleListener]] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""

    # Startup
    logger.info("Instantiating Finlight Data Listener...")
    global fdl, fdq

    fdq = FinlightDataQueues(
        rabbitmq_url=settings.rabbitmq_url,
        message_ttl=settings.message_ttl_ms,
        publisher_confirms=settings.publisher_confirms,
    )
    await fdq.setup_queues()

    # Dynamically instantiate listener class
    listener_classes = {
        "FinlightSimpleListener": FinlightSimpleListener,
        "FinlightDataListener": FinlightDataListener,
    }

    listener_class = listener_classes.get(settings.finlight_data_listener_class)
    if not listener_class:
        raise ValueError(
            f"Unknown listener class: {settings.finlight_data_listener_class}. "
            f"Valid options: {', '.join(listener_classes.keys())}"
        )

    # Build kwargs for listener instantiation
    listener_kwargs: Dict[str, Any] = {
        "api_key": settings.finlight_api_key,
        "queues": fdq,
    }

    # Add optional parameters based on listener class
    if listener_class == FinlightSimpleListener:
        listener_kwargs.update({
            "raw": settings.finlight_raw,
            "include_entities": True,
        })
    elif listener_class == FinlightDataListener:
        listener_kwargs.update({
            "query": settings.finlight_query,
            "tickers": settings.finlight_tickers,
            "sources": settings.finlight_sources,
            "language": settings.finlight_language,
            "max_reconnects": settings.max_reconnects,
        })

    fdl = listener_class(**listener_kwargs)
    logger.info(f"Instantiated {settings.finlight_data_listener_class}")

    if settings.auto_start:
        logger.info("[AUTO-START ENABLED] Starting Finlight Data Listener...")
        await fdl.start()

    yield

    # Shutdown
    logger.info("Shutting down Finlight Data Listener...")
    await stop_websocket_client()
    await fdq.shutdown()


app = FastAPI(
    title="Finlight Data Listener",
    description="Connects to Finlight news stream and publishes articles to RabbitMQ queue",
    lifespan=lifespan,
)


@app.post("/query")
async def query(query: str):
    """Update Finlight article query filter"""
    original_query = copy(settings.finlight_query)
    logger.info(f"Original query: {original_query}")
    try:
        settings.finlight_query = query
        fdl.query = query
        logger.info(f"Query updated to: {query}")
    except Exception as e:
        logger.error(f"Error setting query: {e}")
        logger.error(f"Restoring query to: {original_query}")
        settings.finlight_query = original_query
        fdl.query = original_query
        logger.error("Rollback complete")


@app.post("/tickers")
async def tickers(tickers_list: List[str]):
    """Update Finlight ticker filter"""
    original_tickers = copy(settings.finlight_tickers)
    logger.info(f"Original tickers: {original_tickers}")
    try:
        settings.finlight_tickers = tickers_list
        fdl.tickers = tickers_list
        logger.info(f"Tickers updated to: {tickers_list}")
    except Exception as e:
        logger.error(f"Error setting tickers: {e}")
        logger.error(f"Restoring tickers to: {original_tickers}")
        settings.finlight_tickers = original_tickers
        fdl.tickers = original_tickers
        logger.error("Rollback complete")


@app.post("/sources")
async def sources(sources_list: List[str]):
    """Update Finlight news source filter"""
    original_sources = copy(settings.finlight_sources)
    logger.info(f"Original sources: {original_sources}")
    try:
        settings.finlight_sources = sources_list
        fdl.sources = sources_list
        logger.info(f"Sources updated to: {sources_list}")
    except Exception as e:
        logger.error(f"Error setting sources: {e}")
        logger.error(f"Restoring sources to: {original_sources}")
        settings.finlight_sources = original_sources
        fdl.sources = original_sources
        logger.error("Rollback complete")


@app.post("/language")
async def language(language: str):
    """Update Finlight language filter"""
    original_language = copy(settings.finlight_language)
    logger.info(f"Original language: {original_language}")
    try:
        settings.finlight_language = language
        fdl.language = language
        logger.info(f"Language updated to: {language}")
    except Exception as e:
        logger.error(f"Error setting language: {e}")
        logger.error(f"Restoring language to: {original_language}")
        settings.finlight_language = original_language
        fdl.language = original_language
        logger.error("Rollback complete")


@app.get("/start")
async def start_websocket_client():
    logger.info("Starting Finlight Data Listener...")
    await fdl.start()


@app.get("/stop")
async def stop_websocket_client():
    logger.info("Stopping Finlight Data Listener...")
    await fdl.stop()


@app.get("/restart")
async def restart_websocket_client():
    logger.info("Restarting Finlight Data Listener...")
    await fdl.restart()


@app.get("/")
async def root():
    if fdq.connection_status["connected"] and fdl.connection_status["connected"]:
        ret = "Running"
    elif fdq.connection_status["connected"]:
        ret = "Idle"
    else:
        ret = "Unhealthy"
    return {
        "service": "Finlight Data Listener",
        "status": ret,
        "auto-start": settings.auto_start,
        "container_image": settings.container_image,
        "image_version": settings.image_version,
        "fdq_connection_status": fdq.connection_status,
        "fdl_connection_status": fdl.connection_status,
    }


@app.get("/health", status_code=200)
async def health_check(response: Response):
    """Health check endpoint"""
    status_message = "OK"
    status_code = 1
    if not fdq.connection_status["connected"]:
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
        "fdq_connection_status": fdq.connection_status,
        "fdl_connection_status": fdl.connection_status,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4203)
