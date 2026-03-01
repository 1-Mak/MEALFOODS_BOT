from __future__ import annotations

import asyncio
import logging
import signal
from typing import Any

from app.config import settings
from app.max_client import MaxClient
from app.polling import run_polling

# ------------------------------------------------------------------
# Logging (token-safe: SecretStr prevents leaks)
# ------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-25s  %(levelname)-7s  %(message)s",
)
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


# ==================================================================
# Handler logic
# ==================================================================

client: MaxClient | None = None


async def handle_update(update: dict[str, Any]) -> None:
    """Central dispatcher for all update types."""
    update_type = update.get("update_type")
    logger.info("Received update_type=%s", update_type)

    if update_type == "bot_started":
        await _handle_bot_started(update)
    elif update_type == "message_created":
        await _handle_message(update)
    elif update_type == "message_callback":
        await _handle_callback(update)
    else:
        logger.debug("Unhandled update_type=%s", update_type)


async def _send_greeting(
    *,
    chat_id: int | None = None,
    user_id: int | None = None,
) -> None:
    assert client is not None
    await client.send_message(
        chat_id=chat_id,
        user_id=user_id,
        text=START_TEXT,
        attachments=[START_KEYBOARD],
    )


async def _handle_bot_started(update: dict[str, Any]) -> None:
    """User pressed Start / opened the bot via deeplink."""
    user = update.get("user", {})
    user_id: int | None = user.get("user_id")
    chat_id: int | None = update.get("chat_id")
    await _send_greeting(chat_id=chat_id, user_id=user_id)


async def _handle_message(update: dict[str, Any]) -> None:
    assert client is not None
    message = update.get("message", {})
    body = message.get("body", {})
    text: str = (body.get("text") or "").strip()

    recipient = message.get("recipient", {})
    chat_id: int | None = recipient.get("chat_id")
    sender = message.get("sender", {})
    user_id: int | None = sender.get("user_id")

    if text == "/start":
        await _send_greeting(chat_id=chat_id, user_id=user_id)
    else:
        await client.send_message(
            chat_id=chat_id,
            user_id=user_id,
            text=f"Вы написали: {text}",
        )


async def _handle_callback(update: dict[str, Any]) -> None:
    assert client is not None
    callback = update.get("callback", {})
    callback_id: str | None = callback.get("callback_id")
    payload: str = callback.get("payload", "")

    if not callback_id:
        return

    if payload == "greet":
        # Ответить уведомлением и отправить приветственное сообщение
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


# ==================================================================
# Main
# ==================================================================

async def main() -> None:
    global client

    token = settings.max_bot_token.get_secret_value()
    client = MaxClient(token)

    try:
        me = await client.get_me()
        logger.info(
            "Bot connected: %s (@%s)",
            me.get("first_name"), me.get("username"),
        )
        await run_polling(client, handle_update)
    finally:
        await client.close()
        logger.info("Bot shut down")


if __name__ == "__main__":
    asyncio.run(main())
