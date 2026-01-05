import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Set

import redis.asyncio as redis
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse, RedirectResponse
from kuhl_haus.mdp.components.widget_data_service import WidgetDataService
from pydantic_settings import BaseSettings


class UnauthorizedException(Exception):
    pass


class Settings(BaseSettings):
    # Redis Settings
    redis_url: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # Server Settings
    server_ip: str = os.environ.get("SERVER_IP", "0.0.0.0")
    server_port: int = os.environ.get("SERVER_PORT", 4202)
    log_level: str = os.environ.get("LOG_LEVEL", "INFO").upper()
    container_image: str = os.environ.get("CONTAINER_IMAGE", "Unknown")
    image_version: str = os.environ.get("IMAGE_VERSION", "Unknown")

    # Auth Settings
    auth_enabled: bool = os.environ.get("AUTH_ENABLED", False)
    auth_api_key: str = os.environ.get("AUTH_API_KEY", "secret")


settings = Settings()
logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Global service instance
wds_service: WidgetDataService = None
active_ws_clients: Set[WebSocket] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage WDS lifecycle."""
    global wds_service, active_ws_clients

    # Startup
    active_ws_clients.clear()
    redis_client = redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True
    )
    pubsub_client = redis_client.pubsub()
    wds_service = WidgetDataService(redis_client=redis_client, pubsub_client=pubsub_client)
    await wds_service.start()

    yield

    # Shutdown
    active_ws_clients.clear()
    await wds_service.stop()
    await pubsub_client.close()
    await redis_client.close()


app = FastAPI(
    title="Widget Data Service",
    description="WebSocket interface for client market data subscriptions",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    # return redirect to health_check
    return RedirectResponse(url="/health")


@app.get("/health", status_code=200)
async def health_check(response: Response):
    """Kubernetes health check endpoint."""
    try:
        response.status_code = status.HTTP_200_OK
        return JSONResponse({
            "status": "OK",
            "container_image": settings.container_image,
            "image_version": settings.image_version,
            "active_ws_clients": len(active_ws_clients),
        })
    except Exception as e:
        logger.error(f"Fatal error while processing health check: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for feed subscriptions.

    Client protocol:
        Authenticate:{"action": "auth", "api_key": "secret"}
        Subscribe:   {"action": "subscribe", "feed": "stocks:luld:*"}
        Unsubscribe: {"action": "unsubscribe", "feed": "stocks:luld:*"}
        Snapshot:    {"action": "get", "cache": "stocks:luld:*"}
    """
    await websocket.accept()
    client_info = {
        "headers": json.dumps(websocket.headers.items()),
        "host": websocket.client.host,
        "port": websocket.client.port
    }
    logger.info(f"wds.ws.connected client_info:{client_info}")

    active_feeds: Set[str] = set()
    authenticated: bool = not settings.auth_enabled
    try:
        if not authenticated:
            message = await websocket.receive_text()
            data = json.loads(message)
            action = data.get("action")

            if action == "auth":
                api_key = data.get("api_key")
                # NOTE: This service is designed for internal use and for a
                # single-user. As such, authentication is optional and, if
                # enabled, only supports a single API key, which is set in the
                # AUTH_API_KEY environment variable. Adding support for
                # user-specific API keys is non-trivial.
                # At some point in the future, I may consider adding a more
                # robust authentication system, but this is acceptable for now.
                #
                # [FEATURE] Support for user-specific API keys in Widget Data Service
                # https://github.com/kuhl-haus/kuhl-haus-mdp-servers/issues/1

                if api_key == settings.auth_api_key:
                    authenticated = True
                    logger.info(f"wds.ws.authenticated client_info:{client_info}")
                    await websocket.send_json({"status": "authorized"})
                    active_ws_clients.add(websocket)
                else:
                    await websocket.send_json({"status": "invalid key"})
                    await websocket.close()
                    raise UnauthorizedException("Invalid API key")
            else:
                await websocket.send_json({"status": "unauthorized"})
                await websocket.close()
                raise UnauthorizedException("Unauthorized")
        while authenticated:
            message = await websocket.receive_text()
            data = json.loads(message)
            action = data.get("action")

            if action == "subscribe":
                feed = data.get("feed")
                if feed:
                    await wds_service.subscribe(feed, websocket)
                    active_feeds.add(feed)
                    await websocket.send_json({"status": "subscribed", "feed": feed})

            elif action == "unsubscribe":
                feed = data.get("feed")
                if feed and feed in active_feeds:
                    await wds_service.unsubscribe(feed, websocket)
                    active_feeds.remove(feed)
                    await websocket.send_json({"status": "unsubscribed", "feed": feed})

            elif action == "get":
                cache_key = data.get("cache")
                if cache_key:
                    cached_data = await wds_service.get_cache(cache_key)
                    await websocket.send_json({
                        "cache": cache_key,
                        "data": cached_data
                    })
            else:
                await websocket.send_json({"status": "invalid action"})

    except WebSocketDisconnect:
        client_info = {
            "headers": json.dumps(websocket.headers.items()),
            "host": websocket.client.host,
            "port": websocket.client.port
        }
        logger.info(f"wds.ws.disconnected client_info:{client_info}")
        await wds_service.disconnect(websocket)

    except UnauthorizedException:
        client_info = {
            "headers": json.dumps(websocket.headers.items()),
            "host": websocket.client.host,
            "port": websocket.client.port
        }
        logger.info(f"wds.ws.unauthorized client_info:{client_info}")

    except Exception as e:
        logger.exception(f"wds.ws.unhandled_exception {repr(e)}", exc_info=True)

    finally:
        # Note: the set.remove() method will raise a KeyError if the websocket
        # is not present in the set. Using set.discard(), which will remove
        # the websocket from active_ws_clients if it is present but will not
        # raise an exception.
        active_ws_clients.discard(websocket)
        # Clean up all subscriptions for this client
        for feed in active_feeds:
            await wds_service.unsubscribe(feed, websocket)
