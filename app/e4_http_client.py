"""HTTP client for 1C E4 custom HTTP service (sverka).

Endpoints (confirmed with 1C programmer):
  GET  <E4_HTTP_URL>/GetData    — read data
  POST <E4_HTTP_URL>/GetRequest — write data (create/update/cancel)

TODO: fill in field names once programmer provides response examples.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings
from app.e4_service import E4Counterparty, E4DeliveryPoint, E4Product

logger = logging.getLogger(__name__)


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.e4_http_url,
        auth=(settings.e4_username, settings.e4_password.get_secret_value()),
        timeout=httpx.Timeout(30.0, connect=10.0),
    )


async def _get(params: dict[str, Any]) -> Any:
    async with _client() as c:
        resp = await c.get("/GetData", params=params)
        resp.raise_for_status()
        return resp.json()


async def _post(body: dict[str, Any]) -> Any:
    async with _client() as c:
        resp = await c.post("/GetRequest", json=body)
        resp.raise_for_status()
        return resp.json()


# ------------------------------------------------------------------
# Read methods
# ------------------------------------------------------------------

async def get_counterparties_by_phone(phone: str) -> list[E4Counterparty]:
    """GET /GetData — find counterparties by phone number."""
    # TODO: уточнить у программиста имя параметра и структуру ответа
    # Пример предполагаемого запроса:
    #   GET /GetData?type=counterparties&phone=+79001234567
    # Пример предполагаемого ответа:
    #   [{"guid": "...", "name": "ООО Ромашка"}]
    data = await _get({"type": "counterparties", "phone": phone})
    return [
        E4Counterparty(
            e4_guid=row["guid"],    # TODO: уточнить имя поля
            name=row["name"],       # TODO: уточнить имя поля
            phone=phone,
        )
        for row in (data if isinstance(data, list) else data.get("value", []))
    ]


async def get_delivery_points(counterparty_guid: str) -> list[E4DeliveryPoint]:
    """GET /GetData — delivery addresses for a counterparty."""
    # TODO: уточнить у программиста параметры и структуру ответа
    data = await _get({"type": "delivery_points", "counterparty_guid": counterparty_guid})
    return [
        E4DeliveryPoint(
            e4_guid=row["guid"],              # TODO: уточнить имя поля
            counterparty_guid=counterparty_guid,
            address=row["address"],           # TODO: уточнить имя поля
        )
        for row in (data if isinstance(data, list) else data.get("value", []))
    ]


async def get_product_matrix(counterparty_guid: str) -> list[E4Product]:
    """GET /GetData — products with prices for a counterparty."""
    # TODO: уточнить у программиста параметры и структуру ответа
    data = await _get({"type": "products", "counterparty_guid": counterparty_guid})
    return [
        E4Product(
            e4_guid=row["guid"],                        # TODO: уточнить
            name=row["name"],                           # TODO: уточнить
            unit=row.get("unit", "шт"),                 # TODO: уточнить
            box_multiplicity=int(row.get("box_multiplicity", 1)),  # TODO: уточнить
            net_weight=float(row.get("net_weight", 0)), # TODO: уточнить
            gross_weight=float(row.get("gross_weight", 0)),        # TODO: уточнить
            price=float(row["price"]),                  # TODO: уточнить
            vat_rate=float(row.get("vat_rate", 10)),    # TODO: уточнить
        )
        for row in (data if isinstance(data, list) else data.get("value", []))
    ]


# ------------------------------------------------------------------
# Write methods
# ------------------------------------------------------------------

async def create_order(order_data: dict) -> str:
    """POST /GetRequest — create order in 1C, returns order GUID."""
    # TODO: уточнить у программиста структуру тела запроса
    # Пример предполагаемого запроса:
    # {
    #   "type": "create_order",
    #   "counterparty_guid": "...",
    #   "delivery_point_guid": "...",
    #   "delivery_date": "2026-03-10",
    #   "items": [{"product_guid": "...", "quantity": 10}]
    # }
    result = await _post({"type": "create_order", **order_data})
    return result["order_guid"]   # TODO: уточнить имя поля


async def update_order(order_guid: str, data: dict) -> str:
    """POST /GetRequest — update order in 1C."""
    # TODO: уточнить структуру
    result = await _post({"type": "update_order", "order_guid": order_guid, **data})
    return result.get("status", "ok")


async def cancel_order(order_guid: str) -> str:
    """POST /GetRequest — cancel order in 1C."""
    # TODO: уточнить структуру
    result = await _post({"type": "cancel_order", "order_guid": order_guid})
    return result.get("status", "ok")
