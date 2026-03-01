from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Awaitable, Callable

from app.max_client import MaxClient

logger = logging.getLogger(__name__)

MARKER_FILE = Path(".marker")
POLL_TYPES = ["message_created", "message_callback", "bot_started"]


# ------------------------------------------------------------------
# Marker persistence
# ------------------------------------------------------------------

def _load_marker() -> int | None:
    try:
        text = MARKER_FILE.read_text().strip()
        return int(text) if text else None
    except (FileNotFoundError, ValueError):
        return None


def _save_marker(marker: int) -> None:
    MARKER_FILE.write_text(str(marker))


# ------------------------------------------------------------------
# Polling loop
# ------------------------------------------------------------------

async def run_polling(
    client: MaxClient,
    handler: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:
    """Infinite long-polling loop: fetch updates → dispatch → save marker."""
    marker = _load_marker()
    logger.info("Polling started, initial marker=%s", marker)

    while True:
        try:
            data = await client.get_updates(
                marker=marker,
                timeout=30,
                limit=100,
                types=POLL_TYPES,
            )

            updates: list[dict[str, Any]] = data.get("updates", [])
            new_marker = data.get("marker")

            for update in updates:
                try:
                    await handler(update)
                except Exception:
                    logger.exception("Handler error for update: %s", update)

            if new_marker is not None:
                marker = new_marker
                _save_marker(marker)

        except asyncio.CancelledError:
            logger.info("Polling cancelled")
            raise
        except Exception:
            logger.exception("Polling error, retrying in 5s")
            await asyncio.sleep(5)
