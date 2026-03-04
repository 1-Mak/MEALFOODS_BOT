"""Webhook router — receives status updates from 1C E4."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.database import get_user_by_counterparty_guid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook", tags=["webhook"])

# Bot client is injected at startup via set_bot_client()
_bot_client: Any = None


def set_bot_client(client: Any) -> None:
    global _bot_client
    _bot_client = client


# ------------------------------------------------------------------
# Schema
# ------------------------------------------------------------------

class OrderStatusUpdate(BaseModel):
    order_guid: str
    counterparty_guid: str
    status: str
    stage: str | None = None


# ------------------------------------------------------------------
# Endpoint
# ------------------------------------------------------------------

STATUS_MESSAGES = {
    "Резервируется":       "⏳ Резервируется",
    "Отправлен на сборку": "📦 Отправлен на сборку",
    "Погружено":           "🚚 Погружено",
    "Заблокирован":        "🔒 Заблокирован",
    "Отгружен":            "✅ Отгружен",
    "Отменён":             "❌ Отменён",
}


@router.post("/1c")
async def receive_order_status(body: OrderStatusUpdate) -> dict[str, str]:
    """Called by 1C when order status changes."""
    logger.info(
        "Webhook from 1C: order_guid=%s counterparty=%s status=%s stage=%s",
        body.order_guid, body.counterparty_guid, body.status, body.stage,
    )

    await _notify_manager(body)
    return {"status": "ok"}


async def _notify_manager(body: OrderStatusUpdate) -> None:
    if _bot_client is None:
        return

    user = await get_user_by_counterparty_guid(body.counterparty_guid)
    if not user:
        logger.warning("Webhook: user not found for counterparty %s", body.counterparty_guid)
        return

    label = STATUS_MESSAGES.get(body.status, body.status)
    text = f"Статус вашего заказа изменён:\n{label}"

    try:
        await _bot_client.send_message(user_id=user["max_user_id"], text=text)
    except Exception:
        logger.exception("Failed to send status notification to user %s", user["max_user_id"])
