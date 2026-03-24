import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Union

from fastapi import FastAPI, Response, status
from fastapi.responses import RedirectResponse
from pydantic_settings import BaseSettings

from kuhl_haus.mdp.components.finlight_data_processor import FinlightDataProcessor
from kuhl_haus.mdp.enum.finlight_data_queue import FinlightDataQueue
from kuhl_haus.mdp.helpers.structured_logging import setup_logging


class Settings(BaseSettings):
    # RabbitMQ Settings
    rabbitmq_url: str = os.environ.get("RABBITMQ_URL", "amqp://mdq:mdq@localhost:5672/")

    # Redis Settings
    redis_url: str = os.environ.get("REDIS_URL", "redis://mdc:mdc@localhost:6379/0")

    # Processor settings
    queue_name: str = os.environ.get("FDP_QUEUE_NAME", FinlightDataQueue.NEWS.value)
    prefetch_count: int = os.environ.get("PREFETCH_COUNT", 100)
    max_concurrency: int = os.environ.get("MAX_CONCURRENCY", 500)

    # Server Settings
    server_ip: str = os.environ.get("SERVER_IP", "0.0.0.0")
    server_port: int = os.environ.get("SERVER_PORT", 4204)
    log_level: str = os.environ.get("LOG_LEVEL", "INFO").upper()
    container_image: str = os.environ.get("CONTAINER_IMAGE", "Unknown")
    image_version: str = os.environ.get("IMAGE_VERSION", "Unknown")


settings = Settings()

setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

# Global state
finlight_data_processor: FinlightDataProcessor = None
processor_task: asyncio.Task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global finlight_data_processor, processor_task

    logger.info("Starting Finlight Data Processor...")

    finlight_data_processor = FinlightDataProcessor(
        rabbitmq_url=settings.rabbitmq_url,
        queue_name=settings.queue_name,
        redis_url=settings.redis_url,
        analyzer_class=None,
        prefetch_count=settings.prefetch_count,
        max_concurrent_tasks=settings.max_concurrency,
    )

    processor_task = asyncio.create_task(finlight_data_processor.start())
    logger.info("Finlight Data Processor is running.")

    yield

    # Shutdown
    logger.info("Shutting down Finlight Data Processor...")
    await finlight_data_processor.stop()
    if processor_task and not processor_task.done():
        processor_task.cancel()
    logger.info("Finlight Data Processor stopped.")


app = FastAPI(
    title="Finlight Data Processor",
    description="Consumes Finlight news articles from RabbitMQ and processes them through pluggable analyzers.",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return RedirectResponse(url="/health")


@app.get("/health", status_code=200)
async def health_check(response: Response):
    """Health check endpoint"""
    try:
        return {
            "service": "Finlight Data Processor",
            "status": "OK",
            "status_code": 1,
            "container_image": settings.container_image,
            "image_version": settings.image_version,
            "queue_name": settings.queue_name,
            "prefetch_count": settings.prefetch_count,
            "max_concurrency": settings.max_concurrency,
            "processed": finlight_data_processor.processed,
            "published": finlight_data_processor.published,
            "error": finlight_data_processor.error,
            "processing_error": finlight_data_processor.processing_error,
            "decoding_error": finlight_data_processor.decoding_error,
            "mdq_connected": finlight_data_processor.mdq_connected,
            "mdc_connected": finlight_data_processor.mdc_connected,
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "service": "Finlight Data Processor",
            "status": "ERROR",
            "status_code": 0,
            "container_image": settings.container_image,
            "image_version": settings.image_version,
            "message": "An unhandled exception occurred during health check.",
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4204)
