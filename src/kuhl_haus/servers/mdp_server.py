import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Union

import redis.asyncio as aioredis
from fastapi import FastAPI, Response, status
from fastapi.responses import RedirectResponse
from pydantic_settings import BaseSettings

from massive.rest import RESTClient

from kuhl_haus.mdp.analyzers.top_stocks import TopStocksAnalyzer
from kuhl_haus.mdp.components.market_data_scanner import MarketDataScanner
from kuhl_haus.mdp.components.market_data_cache import MarketDataCache
from kuhl_haus.mdp.models.market_data_cache_keys import MarketDataCacheKeys
from kuhl_haus.mdp.models.market_data_scanner_names import MarketDataScannerNames
from kuhl_haus.mdp.models.massive_data_queue import MassiveDataQueue
from kuhl_haus.mdp.integ.massive_data_processor import MassiveDataProcessor
from kuhl_haus.mdp.helpers.utils import get_massive_api_key
from kuhl_haus.mdp.helpers.process_manager import ProcessManager


class Settings(BaseSettings):
    # Massive/Polygon.io API Key
    massive_api_key: str = get_massive_api_key()

    # RabbitMQ Settings
    rabbitmq_url: str = os.environ.get("RABBITMQ_URL", "amqp://crow:crow@localhost:5672/")
    rabbitmq_host: str = os.environ.get("RABBITMQ_API", "http://crow:crow@localhost:15672/api/")
    message_ttl_ms: int = os.environ.get("MARKET_DATA_MESSAGE_TTL", 5000)  # 5 seconds in milliseconds

    # Redis Settings
    redis_url: str = os.environ.get("REDIS_URL", "redis://redis:redis@localhost:6379/0")

    # Server Settings
    server_ip: str = os.environ.get("SERVER_IP", "0.0.0.0")
    server_port: int = os.environ.get("SERVER_PORT", 4201)
    log_level: str = os.environ.get("LOG_LEVEL", "INFO").upper()
    container_image: str = os.environ.get("CONTAINER_IMAGE", "Unknown")
    image_version: str = os.environ.get("IMAGE_VERSION", "Unknown")


settings = Settings()

logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Global state
market_data_cache: MarketDataCache = None
market_data_scanners: Dict[str, MarketDataScanner] = {}
massive_data_processors: Dict[str, MassiveDataProcessor] = {}
massive_data_queues = [
    MassiveDataQueue.TRADES.value,
    MassiveDataQueue.AGGREGATE.value,
    MassiveDataQueue.QUOTES.value,
    MassiveDataQueue.HALTS.value,
    MassiveDataQueue.NEWS.value,
    MassiveDataQueue.UNKNOWN.value,
]

# Global process manager
process_manager: ProcessManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global process_manager, market_data_cache

    logger.info("Starting Market Data Processor...")
    process_manager = ProcessManager()

    # Start MassiveDataProcessors in separate processes
    for queue in massive_data_queues:
        process_manager.start_worker(
            name=f"mdp_{queue}",
            worker_class=MassiveDataProcessor,
            rabbitmq_url=settings.rabbitmq_url,
            queue_name=queue,
            redis_url=settings.redis_url,
        )

    # Start MarketDataScanners in separate processes
    process_manager.start_worker(
        name=f"scanner_{MarketDataScannerNames.TOP_STOCKS.value}",
        worker_class=MarketDataScanner,
        redis_url=settings.redis_url,
        massive_api_key=settings.massive_api_key,
        subscriptions=[f"{MarketDataCacheKeys.AGGREGATE.value}:*"],
        analyzer_class=TopStocksAnalyzer,
    )

    logger.info("Market Data Processor is running.")

    yield

    # Shutdown
    logger.info("Shutting down Market Data Processor...")
    process_manager.stop_all(timeout=15.0)
    logger.info("Market Data Processor is stopped.")


app = FastAPI(
    title="Market Data Processor",
    description="The MDP is responsible for the heavy lifting which would otherwise constrain the message handling speed of the MDL.",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    # return redirect to health_check
    return RedirectResponse(url="/health")


@app.get("/start")
async def start_scanners():
    # Start all massive data processors
    logger.info("Starting Massive Data Processors...")
    for processor in massive_data_processors.values():
        asyncio.create_task(processor.start())
    logger.info("Massive Data Processors started successfully.")

    logger.info("Starting Market Data Scanners...")
    for k in market_data_scanners.keys():
        logger.info(f"Starting {k}...")
        await market_data_scanners[k].start()
        logger.info(f"{k} started successfully.")
    logger.info("Market Data Scanners started successfully.")


@app.post("/start_scanner")
async def start_scanner(scanner_name: str):
    if scanner_name not in market_data_scanners.keys():
        return {"status": "error", "message": f"Scanner {scanner_name} not found."}
    logger.info(f"Starting {scanner_name}...")
    await market_data_scanners[scanner_name].start()
    logger.info(f"Started {scanner_name} successfully.")
    return {"status": "success", "message": f"{scanner_name} started successfully."}


@app.get("/stop")
async def stop_scanners():
    logger.info("Shutting down Massive Data Processors...")
    for queue in massive_data_queues:
        logger.info(f"Stopping {queue}...")
        await massive_data_processors[queue].stop()
        logger.info(f"{queue} stopped successfully.")
    logger.info("Massive Data Processors stopped successfully.")
    logger.info("Shutting down Market Data Scanners...")
    for k in market_data_scanners.keys():
        logger.info(f"Stopping {k}...")
        await market_data_scanners[k].stop()
        logger.info(f"{k} stopped successfully.")
    logger.info("Market Data Scanners stopped successfully.")


@app.post("/stop_scanner")
async def stop_scanner(scanner_name: str):
    if scanner_name not in market_data_scanners.keys():
        return {"status": "error", "message": f"Scanner {scanner_name} not found."}
    logger.info(f"Stopping {scanner_name}...")
    await market_data_scanners[scanner_name].stop()
    logger.info(f"Stopped {scanner_name} successfully.")
    return {"status": "success", "message": f"{scanner_name} stopped successfully."}


@app.get("/restart")
async def restart_scanners():
    logger.info("Restarting Massive Data Processors...")
    for queue in massive_data_queues:
        logger.info(f"Stopping {queue}...")
        await massive_data_processors[queue].stop()
        logger.info(f"{queue} stopped successfully.")
    logger.info("Starting Massive Data Processors...")
    for processor in massive_data_processors.values():
        asyncio.create_task(processor.start())
    logger.info("Massive Data Processors restarted successfully.")

    logger.info("Restarting Market Data Scanners...")
    for k in market_data_scanners.keys():
        logger.info(f"Restarting {k}...")
        await market_data_scanners[k].restart()
        logger.info(f"{k} restarted successfully.")
    logger.info("Restarting Market Data Scanners restarted successfully.")


@app.post("/restart_scanner")
async def restart_scanner(scanner_name: str):
    if scanner_name not in market_data_scanners.keys():
        return {"status": "error", "message": f"Scanner {scanner_name} not found."}
    logger.info(f"Restarting {scanner_name}...")
    await market_data_scanners[scanner_name].restart()
    logger.info(f"Restarted {scanner_name} successfully.")
    return {"status": "success", "message": f"{scanner_name} restarted successfully."}


@app.get("/health", status_code=200)
async def health_check(response: Response):
    """Health check endpoint - always responsive"""
    try:
        ret: dict[str, Union[str, dict]] = {
            "status": "OK",
            "container_image": settings.container_image,
            "image_version": settings.image_version,
        }

        # Non-blocking status collection
        for queue in massive_data_queues:
            name = f"mdp_{queue}"
            ret[name] = process_manager.get_status(name)

        for scanner_name in [MarketDataScannerNames.TOP_STOCKS.value]:
            name = f"scanner_{scanner_name}"
            ret[name] = process_manager.get_status(name)

        return ret

    except Exception as e:
        logger.error(f"Health check error: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "ERROR", "message": "An unhandled exception occurred during health check."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4201)
