import logging
import os
from contextlib import asynccontextmanager
from typing import List, Union

from fastapi import FastAPI, Response, status
from fastapi.responses import RedirectResponse
from kuhl_haus.mdp.analyzers.leaderboard_analyzer import LeaderboardAnalyzer
from kuhl_haus.mdp.components.massive_data_processor import MassiveDataProcessor
from kuhl_haus.mdp.enum.massive_data_queue import MassiveDataQueue
from kuhl_haus.mdp.helpers.process_manager import ProcessManager
from kuhl_haus.mdp.helpers.utils import get_massive_api_key
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
    redis_url: str = os.environ.get("REDIS_URL", "redis://mdc:mdc@localhost:6379/0")

    # Server Settings
    server_ip: str = os.environ.get("SERVER_IP", "0.0.0.0")
    server_port: int = os.environ.get("SERVER_PORT", 4201)
    log_level: str = os.environ.get("LOG_LEVEL", "INFO").upper()
    container_image: str = os.environ.get("CONTAINER_IMAGE", "Unknown")
    image_version: str = os.environ.get("IMAGE_VERSION", "Unknown")

    # Logging Formats
    logging_format_json: str = ('{ '
                                '"timestamp": "%(asctime)s", '
                                '"filename": "%(filename)s", '
                                '"function": "%(funcName)s", '
                                '"line": "%(lineno)d", '
                                '"level": "%(levelname)s", '
                                '"pid": "%(process)d", '
                                '"thr": "%(thread)d", '
                                '"message": "%(message)s"'
                                '}')
    logging_format: str = os.environ.get("LOGGING_FORMAT", logging_format_json)


settings = Settings()

logging.root.setLevel(settings.log_level)
logging.root.handlers[0].setFormatter(logging.Formatter(settings.logging_format))
logger = logging.getLogger(__name__)


# Global state
massive_data_processors: List[str] = []

# Global process manager
process_manager: ProcessManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global process_manager, massive_data_processors

    logger.info("Starting Market Data Processor...")
    process_manager = ProcessManager()

    # Start MassiveDataProcessors in separate processes
    for i in range(settings.parallelism):
        name = f"mdp_{MassiveDataQueue.AGGREGATE.value}_{i}"
        logger.info(f"Creating MassiveDataProcessor: {name}")
        process_manager.start_worker(
            name=name,
            worker_class=MassiveDataProcessor,
            rabbitmq_url=settings.rabbitmq_url,
            queue_name=MassiveDataQueue.AGGREGATE.value,
            redis_url=settings.redis_url,
            massive_api_key=settings.massive_api_key,
            analyzer_class=LeaderboardAnalyzer,
            prefetch_count=settings.prefetch_count,
            max_concurrent_tasks=settings.max_concurrency,
        )
        massive_data_processors.append(name)

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
        ret: dict[str, Union[str, dict]] = {
            "service": "Market Data Processor",
            "status": "OK",
            "status_code": 1,
            "container_image": settings.container_image,
            "image_version": settings.image_version,
        }

        # Non-blocking status collection
        for name in massive_data_processors:
            ret[name] = process_manager.get_status(name)

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
