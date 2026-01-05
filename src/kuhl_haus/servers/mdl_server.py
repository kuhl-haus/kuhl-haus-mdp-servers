import logging
import json
import os
from contextlib import asynccontextmanager
from copy import copy
from typing import Optional, List, Union

from fastapi import FastAPI, Response, status
from massive.websocket import Feed, Market
from pydantic_settings import BaseSettings

from kuhl_haus.mdp.integ.massive_data_queues import MassiveDataQueues
from kuhl_haus.mdp.integ.massive_data_listener import MassiveDataListener
from kuhl_haus.mdp.helpers.utils import get_massive_api_key


class Settings(BaseSettings):
    # TODO: Retrieve Massive client settings from Service Control Plane API call
    # Massive/Polygon.io API Key
    massive_api_key: str = get_massive_api_key()

    # Massive/Polygon.io Subscription Settings
    # The default values can be overridden via environment variable; use the API to manage at runtime.
    feed: Union[str, Feed] = os.environ.get("MASSIVE_FEED", Feed.RealTime)
    market: Union[str, Market] = os.environ.get("MASSIVE_MARKET", Market.Stocks)
    subscriptions: Optional[List[str]] = (
        json.loads(os.environ.get("MASSIVE_SUBSCRIPTIONS", '["AM.*"]'))
        if os.environ.get("MASSIVE_SUBSCRIPTIONS")
        else ["AM.*"]
    )

    # Additional Massive/Polygon.io Settings - default values can be overridden via environment variables
    raw: bool = os.environ.get("MASSIVE_RAW", False)
    verbose: bool = os.environ.get("MASSIVE_VERBOSE", False)
    max_reconnects: Optional[int] = os.environ.get("MASSIVE_MAX_RECONNECTS", 5)
    secure: bool = os.environ.get("MASSIVE_SECURE", True)

    # Redis Settings
    redis_url: str = os.environ.get("REDIS_URL", "redis://redis:redis@localhost:6379/0")

    # RabbitMQ Settings
    rabbitmq_url: str = os.environ.get("RABBITMQ_URL", "amqp://crow:crow@localhost:5672/")
    rabbitmq_host: str = os.environ.get("RABBITMQ_API", "http://crow:crow@localhost:15672/api/")
    message_ttl_ms: int = os.environ.get("MARKET_DATA_MESSAGE_TTL", 5000)  # 5 seconds in milliseconds

    # Server Settings
    server_ip: str = os.environ.get("SERVER_IP", "0.0.0.0")
    server_port: int = os.environ.get("SERVER_PORT", 4200)
    log_level: str = os.environ.get("LOG_LEVEL", "INFO").upper()
    container_image: str = os.environ.get("CONTAINER_IMAGE", "Unknown")
    image_version: str = os.environ.get("IMAGE_VERSION", "Unknown")
    auto_start: bool = os.environ.get("MARKET_DATA_LISTENER_AUTO_START_ENABLED", False)


settings = Settings()

logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global state
massive_data_queues: Optional[MassiveDataQueues] = None
massive_data_listener: Optional[MassiveDataListener] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""

    # Startup
    logger.info("Instantiating Market Data Listener...")
    global massive_data_listener, massive_data_queues

    massive_data_queues = MassiveDataQueues(
        logger=logger,
        rabbitmq_url=settings.rabbitmq_url,
        message_ttl=settings.message_ttl_ms,
    )
    await massive_data_queues.setup_queues()

    massive_data_listener = MassiveDataListener(
        logger=logger,
        message_handler=massive_data_queues.handle_messages,
        api_key=settings.massive_api_key,
        feed=settings.feed,
        market=settings.market,
        raw=settings.raw,
        verbose=settings.verbose,
        subscriptions=settings.subscriptions,
        max_reconnects=settings.max_reconnects,
        secure=settings.secure,
    )
    logger.info("Market Data Listener is ready.")
    # NOTE: AUTO-START FEATURE IS DISABLED BY DEFAULT.
    # Non-business licenses are limited to a single WebSocket connection for the entire account.
    # The stop, start, and restart API functionality enables manual control of the WebSocket connection.
    #
    # To enable auto-start, set the environment variable MARKET_DATA_LISTENER_AUTO_START_ENABLED=true.
    if settings.auto_start:
        logger.info("[AUTO-START ENABLED]Starting Market Data Listener...")
        await massive_data_listener.start()

    yield

    # Shutdown
    logger.info("Shutting down WebSocket sidecar...")
    await stop_websocket_client()
    await massive_data_queues.shutdown()

app = FastAPI(
    title="Market Data Listener",
    description="Connects to market data provider and publishes to event-specific queues",
    lifespan=lifespan,
)


@app.post("/feed")
async def feed(feed_str: str):
    """Update Massive/Polygon.io feeds"""
    original_feed = copy(settings.feed)
    logger.info(f"Original feed: {original_feed}")
    try:
        if feed_str == Feed.RealTime.value:
            logger.info(f"Setting feed to: {repr(Feed.RealTime)}")
            settings.feed = Feed.RealTime
            massive_data_listener.feed = Feed.RealTime
        elif feed_str == Feed.Delayed.value:
            logger.info(f"Setting feed to: {repr(Feed.Delayed)}")
            settings.feed = Feed.Delayed
            massive_data_listener.feed = Feed.Delayed
        else:
            raise ValueError(f"Invalid feed: {feed_str}")
    except Exception as e:
        logger.error(f"Error setting feed: {e}")
        logger.error(f"Restoring feed to: {original_feed}")
        settings.feed = original_feed
        massive_data_listener.feed = original_feed
        logger.error(f"Current feed: {settings.feed}")
        logger.error("Rollback complete")


@app.post("/market")
async def market(market_str: str):
    """Update Massive/Polygon.io market"""
    original_market = copy(settings.market)
    logger.info(f"Original market: {original_market}")
    try:
        if market_str == Market.Stocks.value:
            logger.info(f"Setting market to: {repr(Market.Stocks)}")
            settings.market = Market.Stocks
            massive_data_listener.market = Market.Stocks
        elif market_str == Market.Options.value:
            logger.info(f"Setting market to: {repr(Market.Options)}")
            settings.market = Market.Options
            massive_data_listener.market = Market.Options
        elif market_str == Market.Indices.value:
            logger.info(f"Setting market to: {repr(Market.Indices)}")
            settings.market = Market.Indices
            massive_data_listener.market = Market.Indices
        else:
            raise ValueError(f"Invalid market: {market_str}")
    except Exception as e:
        logger.error(f"Error setting market: {e}")
        logger.error(f"Restoring market to: {original_market}")
        settings.market = original_market
        massive_data_listener.market = original_market
        logger.error(f"Current market: {settings.market}")
        logger.error("Rollback complete")


@app.post("/subscriptions")
async def subscriptions(subscriptions_list: List[str]):
    """Update Massive/Polygon.io subscriptions"""
    original_subscriptions = copy(settings.subscriptions)
    logger.info(f"Original subscriptions: {original_subscriptions}")
    try:
        settings.subscriptions = []
        for sub in subscriptions_list:
            # Only add subscriptions that start with one of the following prefixes:
            # "A.*", "AM.*", "T.*", "Q.*", "LULD.*"
            if (sub.startswith("A.") or
                    sub.startswith("AM.") or
                    sub.startswith("T.") or
                    sub.startswith("Q.") or
                    sub.startswith("LULD.")):
                logger.info(f"Adding subscription: {sub}")
                settings.subscriptions.append(sub)
        massive_data_listener.subscriptions = settings.subscriptions
        logger.info(f"Current subscriptions: {settings.subscriptions}")
    except Exception as e:
        logger.error(f"Error setting subscriptions: {e}")
        logger.error(f"Restoring subscriptions to: {original_subscriptions}")
        settings.subscriptions = original_subscriptions
        massive_data_listener.subscriptions = original_subscriptions
        logger.error(f"Current subscriptions: {settings.subscriptions}")
        logger.error("Rollback complete")


@app.get("/start")
async def start_websocket_client():
    logger.info("Starting Market Data Listener...")
    await massive_data_listener.start()


@app.get("/stop")
async def stop_websocket_client():
    logger.info("Stopping Market Data Listener...")
    await massive_data_listener.stop()


@app.get("/restart")
async def restart_websocket_client():
    logger.info("Restarting Market Data Listener...")
    await massive_data_listener.restart()


@app.get("/")
async def root():
    if massive_data_queues.connection_status["connected"] and massive_data_listener.connection_status["connected"]:
        ret = "Running"
    elif massive_data_queues.connection_status["connected"]:
        ret = "Idle"
    else:
        ret = "Unhealthy"
    return {
        "service": "Market Data Listener",
        "status": ret,
        "auto-start": settings.auto_start,
        "container_image": settings.container_image,
        "image_version": settings.image_version,
        "mdq_connection_status": massive_data_queues.connection_status,
        "mdl_connection_status": massive_data_listener.connection_status
    }


@app.get("/health", status_code=200)
async def health_check(response: Response):
    """Health check endpoint"""
    # The server should be connected to MDQ even when the WebSocket client is not running.
    status_message = "OK"
    if not massive_data_queues.connection_status["connected"]:
        status_message = "Unhealthy"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    # TODO: Investigate if this caused health check failures in production during off-hours.
    # if settings.auto_start and not massive_data_listener.connection_status["connected"]:
    #     status_message = "Unhealthy"
    #     response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "service": "Market Data Listener",
        "status": status_message,
        "auto-start": settings.auto_start,
        "container_image": settings.container_image,
        "image_version": settings.image_version,
        "mdq_connection_status": massive_data_queues.connection_status,
        "mdl_connection_status": massive_data_listener.connection_status
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4200)
