import logging
import os
from contextlib import asynccontextmanager
from typing import List, Union

from fastapi import FastAPI, Response, status
from fastapi.responses import RedirectResponse
from kuhl_haus.mdp.analyzers.leaderboard_analyzer import LeaderboardAnalyzer
from kuhl_haus.mdp.analyzers.massive_data_analyzer import MassiveDataAnalyzer
from kuhl_haus.mdp.analyzers.top_trades_analyzer import TopTradesAnalyzer
from kuhl_haus.mdp.components.massive_data_processor import MassiveDataProcessor
from kuhl_haus.mdp.enum.massive_data_queue import MassiveDataQueue
from kuhl_haus.mdp.helpers.process_manager import ProcessManager
from kuhl_haus.mdp.analyzers.analyzer import AnalyzerOptions
from kuhl_haus.mdp.helpers.utils import get_massive_api_key
from kuhl_haus.mdp.helpers.structured_logging import setup_logging
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Number of parallel MassiveDataProcessors to run
    parallelism: int = os.environ.get("PARALLELISM", 10)
    prefetch_count: int = os.environ.get("PREFETCH_COUNT", 10)
    max_concurrency: int = os.environ.get("MAX_CONCURRENCY", 100)

    # Massive/Polygon.io API Key
    massive_api_key: str = get_massive_api_key()

    # RabbitMQ Settings
    rabbitmq_url: str = os.environ.get("RABBITMQ_URL", "amqp://mdq:mdq@localhost:5672/")

    # Redis Settings
    mdc_redis_url: str = os.environ.get("MDC_REDIS_URL", "redis://mdc:mdc@localhost:6379/0")
    wdc_redis_url: str = os.environ.get("WDC_REDIS_URL", "redis://mdc:mdc@localhost:6379/1")

    # Server Settings
    server_ip: str = os.environ.get("SERVER_IP", "0.0.0.0")
    server_port: int = os.environ.get("SERVER_PORT", 4201)
    log_level: str = os.environ.get("LOG_LEVEL", "INFO").upper()
    container_image: str = os.environ.get("CONTAINER_IMAGE", "Unknown")
    image_version: str = os.environ.get("IMAGE_VERSION", "Unknown")


settings = Settings()

setup_logging(settings.log_level)
logger = logging.getLogger(__name__)


# Global state - processors grouped by queue type
massive_data_processors: dict[str, List[str]] = {
    MassiveDataQueue.AGGREGATE.value: [],
    MassiveDataQueue.TRADES.value: [],
    MassiveDataQueue.QUOTES.value: [],
    MassiveDataQueue.HALTS.value: [],
}

# Global process manager
process_manager: ProcessManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global process_manager, massive_data_processors

    logger.info("Starting Market Data Processor...")
    process_manager = ProcessManager()

    analyzer_options = AnalyzerOptions(
        redis_url=settings.mdc_redis_url,
        massive_api_key=settings.massive_api_key,
    )

    # Start MassiveDataProcessors in separate processes
    for i in range(settings.parallelism):
        name = f"mdp_{MassiveDataQueue.AGGREGATE.value}_{i}"
        logger.info(f"Creating MassiveDataProcessor: {name}")
        process_manager.start_worker(
            name=name,
            worker_class=MassiveDataProcessor,
            rabbitmq_url=settings.rabbitmq_url,
            queue_name=MassiveDataQueue.AGGREGATE.value,
            redis_url=settings.wdc_redis_url,
            analyzer_class=LeaderboardAnalyzer,
            analyzer_options=analyzer_options,
            prefetch_count=settings.prefetch_count,
            max_concurrent_tasks=settings.max_concurrency,
        )
        massive_data_processors[MassiveDataQueue.AGGREGATE.value].append(name)

    for i in range(settings.parallelism):
        name = f"mdp_{MassiveDataQueue.TRADES.value}_{i}"
        logger.info(f"Creating MassiveDataProcessor: {name}")
        process_manager.start_worker(
            name=name,
            worker_class=MassiveDataProcessor,
            rabbitmq_url=settings.rabbitmq_url,
            queue_name=MassiveDataQueue.TRADES.value,
            redis_url=settings.wdc_redis_url,
            analyzer_class=TopTradesAnalyzer,
            analyzer_options=analyzer_options,
            prefetch_count=settings.prefetch_count,
            max_concurrent_tasks=settings.max_concurrency,
        )
        massive_data_processors[MassiveDataQueue.TRADES.value].append(name)

    for i in range(settings.parallelism):
        name = f"mdp_{MassiveDataQueue.QUOTES.value}_{i}"
        logger.info(f"Creating MassiveDataProcessor: {name}")
        process_manager.start_worker(
            name=name,
            worker_class=MassiveDataProcessor,
            rabbitmq_url=settings.rabbitmq_url,
            queue_name=MassiveDataQueue.QUOTES.value,
            redis_url=settings.wdc_redis_url,
            analyzer_class=MassiveDataAnalyzer,
            analyzer_options=analyzer_options,
            prefetch_count=settings.prefetch_count,
            max_concurrent_tasks=settings.max_concurrency,
        )
        massive_data_processors[MassiveDataQueue.QUOTES.value].append(name)

    for i in range(settings.parallelism):
        name = f"mdp_{MassiveDataQueue.HALTS.value}_{i}"
        logger.info(f"Creating MassiveDataProcessor: {name}")
        process_manager.start_worker(
            name=name,
            worker_class=MassiveDataProcessor,
            rabbitmq_url=settings.rabbitmq_url,
            queue_name=MassiveDataQueue.HALTS.value,
            redis_url=settings.wdc_redis_url,
            analyzer_class=MassiveDataAnalyzer,
            analyzer_options=analyzer_options,
            prefetch_count=settings.prefetch_count,
            max_concurrent_tasks=settings.max_concurrency,
        )
        massive_data_processors[MassiveDataQueue.HALTS.value].append(name)

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


@app.get("/health", status_code=200)
async def health_check(response: Response):
    """Health check endpoint - always responsive"""
    try:
        ret: dict[str, Union[str, int, dict, list]] = {
            "service": "Market Data Processor",
            "status": "OK",
            "status_code": 1,
            "container_image": settings.container_image,
            "image_version": settings.image_version,
            "parallelism": settings.parallelism,
            "prefetch_count": settings.prefetch_count,
            "max_concurrency": settings.max_concurrency,
        }

        # Non-blocking status collection grouped by queue type
        for queue_type, processor_names in massive_data_processors.items():
            ret[f"{queue_type}_processors"] = [
                process_manager.get_status(name) for name in processor_names
            ]

        return ret

    except Exception as e:
        logger.error(f"Health check error: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "service": "Market Data Processor",
            "status": "ERROR",
            "status_code": 0,
            "container_image": settings.container_image,
            "image_version": settings.image_version,
            "message": "An unhandled exception occurred during health check."
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4201)
