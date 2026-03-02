"""Bot update handlers for MAX messenger."""
from __future__ import annotations

import logging
from typing import Any

from app.config import settings
from app.database import get_user_by_max_id, upsert_user
from app.e4_service import get_counterparties_by_phone
from app.max_client import MaxClient

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Texts
# ------------------------------------------------------------------

START_TEXT = (
    "Привет! Я бот MealFoods.\n"
    "Для начала работы необходимо авторизоваться."
)

PHONE_NOT_FOUND_TEXT = (
    "К сожалению, ваш номер телефона не найден в системе.\n"
    "Обратитесь в отдел клиентского сервиса."
)

NO_PHONE_TEXT = "Не удалось получить номер телефона. Попробуйте ещё раз."

# ------------------------------------------------------------------
# Keyboards
# ------------------------------------------------------------------

CONTACT_KEYBOARD: dict[str, Any] = {
    "type": "inline_keyboard",
    "payload": {
        "buttons": [[
            {
                "type": "request_contact",
                "text": "Авторизоваться",
            },
        ]],
    },
}


def _open_app_keyboard() -> dict[str, Any]:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [[
                {
                    "type": "link",
                    "text": "Личный кабинет",
                    "url": settings.miniapp_url,
                },
            ]],
        },
    }


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
# Handlers
# ------------------------------------------------------------------

async def _handle_bot_started(client: MaxClient, update: dict[str, Any]) -> None:
    user = update.get("user", {})
    user_id: int | None = user.get("user_id")
    chat_id: int | None = update.get("chat_id")

    # If user already registered — send open_app right away
    if user_id:
        record = await get_user_by_max_id(user_id)
        if record and record.get("phone"):
            await client.send_message(
                chat_id=chat_id,
                user_id=user_id,
                text="С возвращением! Нажмите кнопку для входа.",
                attachments=[_open_app_keyboard()],
            )
            return

    await _send_contact_request(client, chat_id=chat_id, user_id=user_id)


async def _handle_message(client: MaxClient, update: dict[str, Any]) -> None:
    message = update.get("message", {})
    body = message.get("body", {})
    text: str = (body.get("text") or "").strip()

    recipient = message.get("recipient", {})
    chat_id: int | None = recipient.get("chat_id")
    sender = message.get("sender", {})
    user_id: int | None = sender.get("user_id")

    # Check for shared contact in attachments
    phone = _extract_phone(message)
    if phone:
        await _handle_contact(client, chat_id=chat_id, user_id=user_id, phone=phone)
        return

    if text == "/start":
        await _send_contact_request(client, chat_id=chat_id, user_id=user_id)
        return

    # Any other text — check if user is registered
    if user_id:
        record = await get_user_by_max_id(user_id)
        if record and record.get("phone"):
            await client.send_message(
                chat_id=chat_id,
                user_id=user_id,
                text="Нажмите кнопку для входа в личный кабинет.",
                attachments=[_open_app_keyboard()],
            )
            return

    await _send_contact_request(client, chat_id=chat_id, user_id=user_id)


async def _handle_callback(client: MaxClient, update: dict[str, Any]) -> None:
    callback = update.get("callback", {})
    callback_id: str | None = callback.get("callback_id")
    if callback_id:
        await client.answer_callback(callback_id, notification="Принято")


# ------------------------------------------------------------------
# Contact processing
# ------------------------------------------------------------------

async def _send_contact_request(
    client: MaxClient,
    *,
    chat_id: int | None = None,
    user_id: int | None = None,
) -> None:
    await client.send_message(
        chat_id=chat_id,
        user_id=user_id,
        text=START_TEXT,
        attachments=[CONTACT_KEYBOARD],
    )


def _extract_phone(message: dict[str, Any]) -> str | None:
    """Try to extract phone number from contact attachment."""
    body = message.get("body", {})
    attachments = body.get("attachments") or []

    for att in attachments:
        if att.get("type") == "contact":
            payload = att.get("payload", {})
            # Try direct phone field
            if payload.get("phone"):
                return payload["phone"]
            # Try VCF info (vCard format)
            vcf = payload.get("vcf_info") or payload.get("vcf_string") or ""
            for line in vcf.split("\n"):
                if line.upper().startswith("TEL"):
                    return line.split(":")[-1].strip()
            # Try tam_info
            tam = payload.get("tam_info", {})
            if tam.get("phone"):
                return tam["phone"]
    return None


def _normalize_phone(phone: str) -> str:
    """Normalize phone to +7XXXXXXXXXX format."""
    digits = "".join(c for c in phone if c.isdigit())
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if not digits.startswith("7"):
        digits = "7" + digits
    return "+" + digits


async def _handle_contact(
    client: MaxClient,
    *,
    chat_id: int | None,
    user_id: int | None,
    phone: str,
) -> None:
    """Handle shared contact: lookup phone in 1C, save user, send open_app."""
    normalized = _normalize_phone(phone)
    logger.info("Contact shared: user_id=%s, phone=%s", user_id, normalized)

    counterparties = await get_counterparties_by_phone(normalized)

    if not counterparties:
        await client.send_message(
            chat_id=chat_id,
            user_id=user_id,
            text=PHONE_NOT_FOUND_TEXT,
        )
        return

    # Save user with phone and first counterparty
    if user_id:
        await upsert_user(
            max_user_id=user_id,
            phone=normalized,
            counterparty_guid=counterparties[0].e4_guid,
            counterparty_name=counterparties[0].name,
        )

    names = ", ".join(cp.name for cp in counterparties)
    text = f"Найдены контрагенты: {names}\n\nНажмите кнопку для входа в личный кабинет."

    await client.send_message(
        chat_id=chat_id,
        user_id=user_id,
        text=text,
        attachments=[_open_app_keyboard()],
    )
