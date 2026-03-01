"""Bot update handlers for MAX messenger."""
from __future__ import annotations

import logging
from typing import Any

from app.max_client import MaxClient

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Bot responses
# ------------------------------------------------------------------

START_TEXT = "Привет! Я бот MAX MealFoods.\nНажмите кнопку ниже."

START_KEYBOARD: dict[str, Any] = {
    "type": "inline_keyboard",
    "payload": {
        "buttons": [[
            {
                "type": "callback",
                "text": "Поздороваться",
                "payload": "greet",
            },
        ]],
    },
}

GREET_TEXT = "Рады вас видеть! Добро пожаловать в MAX MealFoods."


# ------------------------------------------------------------------
# Handler factory
# ------------------------------------------------------------------

def make_handler(client: MaxClient):
    """Return an update handler bound to the given MaxClient."""

    async def handle_update(update: dict[str, Any]) -> None:
        update_type = update.get("update_type")
        logger.info("Received update_type=%s", update_type)

        if update_type == "bot_started":
            await _handle_bot_started(client, update)
        elif update_type == "message_created":
            await _handle_message(client, update)
        elif update_type == "message_callback":
            await _handle_callback(client, update)
        else:
            logger.debug("Unhandled update_type=%s", update_type)

    return handle_update


# ------------------------------------------------------------------
# Individual handlers
# ------------------------------------------------------------------

async def _send_greeting(
    client: MaxClient,
    *,
    chat_id: int | None = None,
    user_id: int | None = None,
) -> None:
    await client.send_message(
        chat_id=chat_id,
        user_id=user_id,
        text=START_TEXT,
        attachments=[START_KEYBOARD],
    )


async def _handle_bot_started(client: MaxClient, update: dict[str, Any]) -> None:
    user = update.get("user", {})
    user_id: int | None = user.get("user_id")
    chat_id: int | None = update.get("chat_id")
    await _send_greeting(client, chat_id=chat_id, user_id=user_id)


async def _handle_message(client: MaxClient, update: dict[str, Any]) -> None:
    message = update.get("message", {})
    body = message.get("body", {})
    text: str = (body.get("text") or "").strip()

    recipient = message.get("recipient", {})
    chat_id: int | None = recipient.get("chat_id")
    sender = message.get("sender", {})
    user_id: int | None = sender.get("user_id")

    if text == "/start":
        await _send_greeting(client, chat_id=chat_id, user_id=user_id)
    else:
        await client.send_message(
            chat_id=chat_id,
            user_id=user_id,
            text=f"Вы написали: {text}",
        )


async def _handle_callback(client: MaxClient, update: dict[str, Any]) -> None:
    callback = update.get("callback", {})
    callback_id: str | None = callback.get("callback_id")
    payload: str = callback.get("payload", "")

    if not callback_id:
        return

    if payload == "greet":
        message = update.get("message", {})
        recipient = message.get("recipient", {})
        chat_id: int | None = recipient.get("chat_id")
        sender = message.get("sender", {})
        user_id: int | None = sender.get("user_id")

        await client.answer_callback(callback_id, notification="Принято")
        await client.send_message(
            chat_id=chat_id,
            user_id=user_id,
            text=GREET_TEXT,
        )
    else:
        await client.answer_callback(callback_id, notification="Принято")
