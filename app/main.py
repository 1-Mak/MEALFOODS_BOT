from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.bot import make_handler
from app.config import settings
from app.database import init_db
from app.max_client import MaxClient
from app.polling import run_polling
from app.routers import auth, counterparties, orders, products, webhook
from app.routers.webhook import set_bot_client

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-25s  %(levelname)-7s  %(message)s",
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Globals
# ------------------------------------------------------------------

client: MaxClient | None = None
_polling_task: asyncio.Task[None] | None = None


# ------------------------------------------------------------------
# Lifespan
# ------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_app: FastAPI):  # noqa: ANN201
    global client, _polling_task

    await init_db()
    logger.info("Database ready")

    # Start MAX bot (non-critical — API works without bot)
    token = settings.max_bot_token.get_secret_value()
    client = MaxClient(token)

    try:
        me = await client.get_me()
        username = me.get("username", "")
        logger.info("Bot connected: %s (@%s)", me.get("first_name"), username)
        if username:
            logger.info(
                "Bot deep link (triggers bot_started every time): https://max.ru/%s?start=1",
                username,
            )

        try:
            subs = await client.get_subscriptions()
            if subs.get("subscriptions"):
                await client.delete_webhook()
                logger.info("Webhook deleted — polling will now receive all events")
            else:
                logger.info("No webhook subscriptions found")
        except Exception:
            logger.warning("Failed to check/delete webhook (non-critical)", exc_info=True)

        try:
            await client.set_my_commands([
                {"name": "start", "description": "Начать работу или авторизоваться."},
            ])
            logger.info("Bot commands registered")
        except Exception:
            logger.warning("Failed to register bot commands (non-critical)", exc_info=True)

        set_bot_client(client)

        handler = make_handler(client)
        _polling_task = asyncio.create_task(run_polling(client, handler))
        logger.info("Polling task started")
    except Exception:
        logger.warning("MAX API unavailable — bot disabled, API-only mode", exc_info=True)

    yield

    # Shutdown
    if _polling_task is not None:
        _polling_task.cancel()
        try:
            await _polling_task
        except asyncio.CancelledError:
            pass
    await client.close()
    logger.info("Bot shut down")


# ------------------------------------------------------------------
# FastAPI app
# ------------------------------------------------------------------

app = FastAPI(title="MAX MealFoods Bot", lifespan=lifespan)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return detailed error info instead of generic 500."""
    import httpx
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    detail = str(exc)
    if isinstance(exc, httpx.HTTPStatusError):
        detail = f"1C returned {exc.response.status_code} for {exc.request.url}"
    return JSONResponse(
        status_code=500,
        content={"detail": detail, "type": type(exc).__name__},
    )


app.include_router(auth.router)
app.include_router(counterparties.router)
app.include_router(orders.router)
app.include_router(products.router)
app.include_router(webhook.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "e4_http": bool(__import__("app.config", fromlist=["settings"]).settings.e4_http_url)}
