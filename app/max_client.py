from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_BASE = 1.0
BACKOFF_FACTOR = 2.0


class MaxClient:
    """Async HTTP client for MAX Bot API (https://platform-api.max.ru)."""

    def __init__(self, token: str) -> None:
        self._client = httpx.AsyncClient(
            base_url="https://platform-api.max.ru",
            headers={"Authorization": token},
            timeout=httpx.Timeout(60.0, connect=10.0),
        )

    async def close(self) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Internal: request with retry
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        last_exc: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                resp = await self._client.request(
                    method, url, params=params, json=json,
                )
                if resp.status_code >= 500:
                    logger.warning(
                        "Server error %s on %s %s (attempt %d/%d)",
                        resp.status_code, method, url,
                        attempt + 1, MAX_RETRIES,
                    )
                    last_exc = httpx.HTTPStatusError(
                        f"Server error {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                    await asyncio.sleep(BACKOFF_BASE * (BACKOFF_FACTOR ** attempt))
                    continue

                resp.raise_for_status()
                return resp.json()

            except httpx.TransportError as exc:
                logger.warning(
                    "Transport error on %s %s (attempt %d/%d): %s",
                    method, url, attempt + 1, MAX_RETRIES, exc,
                )
                last_exc = exc
                await asyncio.sleep(BACKOFF_BASE * (BACKOFF_FACTOR ** attempt))

        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    async def get_me(self) -> dict[str, Any]:
        """GET /me — bot info."""
        return await self._request("GET", "/me")

    async def send_message(
        self,
        *,
        chat_id: int | None = None,
        user_id: int | None = None,
        text: str,
        fmt: str = "markdown",
        attachments: list[dict[str, Any]] | None = None,
        notify: bool = True,
    ) -> dict[str, Any]:
        """POST /messages?chat_id=<id> or ?user_id=<id>."""
        params: dict[str, Any] = {}
        if chat_id is not None:
            params["chat_id"] = chat_id
        elif user_id is not None:
            params["user_id"] = user_id
        else:
            raise ValueError("Either chat_id or user_id must be provided")

        body: dict[str, Any] = {
            "text": text,
            "format": fmt,
            "notify": notify,
        }
        if attachments:
            body["attachments"] = attachments

        return await self._request("POST", "/messages", params=params, json=body)

    async def get_updates(
        self,
        *,
        marker: int | None = None,
        timeout: int = 30,
        limit: int = 100,
        types: list[str] | None = None,
    ) -> dict[str, Any]:
        """GET /updates — long polling.

        ``types`` is sent as repeated query params (?types=a&types=b);
        httpx handles this automatically when the value is a list.
        """
        params: dict[str, Any] = {"timeout": timeout, "limit": limit}
        if marker is not None:
            params["marker"] = marker
        if types:
            params["types"] = types
        return await self._request("GET", "/updates", params=params)

    async def answer_callback(
        self,
        callback_id: str,
        *,
        notification: str | None = None,
        message: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST /answers?callback_id=<id>."""
        body: dict[str, Any] = {}
        if notification is not None:
            body["notification"] = notification
        if message is not None:
            body["message"] = message
        return await self._request(
            "POST", "/answers", params={"callback_id": callback_id}, json=body,
        )
