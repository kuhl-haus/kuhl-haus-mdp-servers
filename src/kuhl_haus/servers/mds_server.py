import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status
from fastapi.responses import RedirectResponse
from pydantic_settings import BaseSettings

from kuhl_haus.mdp.analyzers.analyzer import AnalyzerOptions
from kuhl_haus.mdp.analyzers.daily_range_analyzer import DailyRangeAnalyzer
from kuhl_haus.mdp.components.market_data_scanner import MarketDataScanner
from kuhl_haus.mdp.enum.widget_data_cache_keys import WidgetDataCacheKeys
from kuhl_haus.mdp.enum.widget_data_cache_limits import WidgetDataCacheLimits
from kuhl_haus.mdp.helpers.structured_logging import setup_logging


class Settings(BaseSettings):
    # Redis Settings (WDC only — MDS never touches MDC)
    wdc_redis_url: str = os.environ.get("WDC_REDIS_URL", "redis://mdc:mdc@localhost:6379/1")

    # Processor Settings
    dra_cache_list_max: int = os.environ.get("DRA_CACHE_LIST_MAX", WidgetDataCacheLimits.DRA_CACHE_LIST_MAX.value)

    # Massive Settings
    massive_api_key: str = os.environ.get("MASSIVE_API_KEY", "")

    # Server Settings
    server_ip: str = os.environ.get("SERVER_IP", "0.0.0.0")
    server_port: int = os.environ.get("SERVER_PORT", 4205)
    log_level: str = os.environ.get("LOG_LEVEL", "INFO").upper()
    container_image: str = os.environ.get("CONTAINER_IMAGE", "Unknown")
    image_version: str = os.environ.get("IMAGE_VERSION", "Unknown")


settings = Settings()

setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

# Global state
market_data_scanner: MarketDataScanner = None
scanner_task: asyncio.Task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global market_data_scanner, scanner_task

    logger.info("Starting Market Data Scanner...")

    analyzer_options = AnalyzerOptions(
        redis_url=settings.wdc_redis_url,
        massive_api_key=settings.massive_api_key or None,
        kwargs={
            "dra_cache_list_max": settings.dra_cache_list_max
        },
    )

    market_data_scanner = MarketDataScanner(
        redis_url=settings.wdc_redis_url,
        subscriptions=[f"{WidgetDataCacheKeys.QUOTE.value}:*"],
        analyzer_class=DailyRangeAnalyzer,
        analyzer_options=analyzer_options,
    )

    scanner_task = asyncio.create_task(market_data_scanner.start())
    logger.info("Market Data Scanner is running.")

    yield

    # Shutdown
    logger.info("Shutting down Market Data Scanner...")
    await market_data_scanner.stop()
    if scanner_task and not scanner_task.done():
        scanner_task.cancel()
    logger.info("Market Data Scanner stopped.")


app = FastAPI(
    title="Market Data Scanner",
    description="Redis pub/sub consumer that performs secondary analysis on market data — event correlation, alert generation, trend analysis, and pattern recognition — through pluggable analyzers.",
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
            "service": "Market Data Scanner",
            "status": "OK",
            "status_code": 1,
            "container_image": settings.container_image,
            "image_version": settings.image_version,
            "mdc_connected": market_data_scanner.mdc_connected,
            "running": market_data_scanner.running,
            "processed": market_data_scanner.processed,
            "published_results": market_data_scanner.published_results,
            "empty_results": market_data_scanner.empty_results,
            "decoding_errors": market_data_scanner.decoding_errors,
            "errors": market_data_scanner.errors,
            "restarts": market_data_scanner.restarts,
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "service": "Market Data Scanner",
            "status": "ERROR",
            "status_code": 0,
            "container_image": settings.container_image,
            "image_version": settings.image_version,
            "message": "An unhandled exception occurred during health check.",
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4205)
