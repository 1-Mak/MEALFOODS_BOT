"""HTTP client for 1C custom HTTP service (integrationMax).

Endpoints (confirmed with 1C programmer):
  GET  <E4_HTTP_URL>/Ping                              — проверка доступности
  GET  <E4_HTTP_URL>/GetCounterpartys/PhoneNumber={p}  — контрагент по номеру телефона
  GET  <E4_HTTP_URL>/GetData                           — точки доставки, номенклатура, заказы
  POST <E4_HTTP_URL>/GetRequest                        — создание/обновление/отмена заказа

TODO: уточнить у программиста имена полей ответа.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings
from app.e4_service import E4Counterparty, E4DeliveryPoint, E4Product

logger = logging.getLogger(__name__)


def _client() -> httpx.AsyncClient:
    base_url = settings.e4_http_url.rstrip("/") + "/"
    return httpx.AsyncClient(
        base_url=base_url,
        auth=(settings.e4_username, settings.e4_password.get_secret_value()),
        timeout=httpx.Timeout(30.0, connect=10.0),
    )


async def ping() -> bool:
    """GET /Ping — проверка доступности 1С базы."""
    async with _client() as c:
        try:
            resp = await c.get("Ping")
            resp.raise_for_status()
            logger.info("1C ping OK: %s", resp.text)
            return True
        except Exception as exc:
            logger.error("1C ping FAILED: %s", exc)
            return False


async def _get(params: dict[str, Any]) -> Any:
    async with _client() as c:
        resp = await c.get("GetData", params=params)
        resp.raise_for_status()
        return resp.json()


async def _post(body: dict[str, Any]) -> Any:
    async with _client() as c:
        resp = await c.post("GetRequest", json=body)
        resp.raise_for_status()
        return resp.json()


# ------------------------------------------------------------------
# Read methods
# ------------------------------------------------------------------

async def get_orders(counterparty_guid: str) -> list:
    """GET /GetData — list orders for a counterparty."""
    # TODO: уточнить у программиста параметры и структуру ответа
    from app.e4_service import E4Order, E4OrderItem
    data = await _get({"type": "orders", "counterparty_guid": counterparty_guid})
    rows = data if isinstance(data, list) else data.get("РезультатВыгрузки", [])
    result = []
    for row in rows:
        items = [
            E4OrderItem(
                product_guid=i["product_guid"],   # TODO: уточнить
                product_name=i["product_name"],   # TODO: уточнить
                quantity=int(i["quantity"]),       # TODO: уточнить
                price=float(i["price"]),           # TODO: уточнить
                box_multiplicity=int(i.get("box_multiplicity", 1)),
                net_weight=float(i.get("net_weight", 0)),
                gross_weight=float(i.get("gross_weight", 0)),
            )
            for i in row.get("items", [])          # TODO: уточнить
        ]
        result.append(E4Order(
            e4_guid=row["guid"],                   # TODO: уточнить
            counterparty_guid=counterparty_guid,
            delivery_point_guid=row["delivery_point_guid"],  # TODO: уточнить
            delivery_date=row["delivery_date"],    # TODO: уточнить
            status=row["status"],                  # TODO: уточнить
            stage=row["stage"],                    # TODO: уточнить
            total_price=float(row.get("total_price", 0)),
            created_at=row.get("created_at", ""),  # TODO: уточнить
            items=items,
        ))
    return result


async def get_order(e4_guid: str):
    """GET /GetData — single order with items."""
    # TODO: уточнить у программиста параметры и структуру ответа
    from app.e4_service import E4Order, E4OrderItem
    data = await _get({"type": "order", "guid": e4_guid})
    rows = data if isinstance(data, list) else data.get("РезультатВыгрузки", [])
    if not rows:
        return None
    row = rows[0]
    items = [
        E4OrderItem(
            product_guid=i["product_guid"],        # TODO: уточнить
            product_name=i["product_name"],        # TODO: уточнить
            quantity=int(i["quantity"]),
            price=float(i["price"]),
            box_multiplicity=int(i.get("box_multiplicity", 1)),
            net_weight=float(i.get("net_weight", 0)),
            gross_weight=float(i.get("gross_weight", 0)),
        )
        for i in row.get("items", [])
    ]
    return E4Order(
        e4_guid=row["guid"],                       # TODO: уточнить
        counterparty_guid=row["counterparty_guid"],# TODO: уточнить
        delivery_point_guid=row["delivery_point_guid"],
        delivery_date=row["delivery_date"],
        status=row["status"],
        stage=row["stage"],
        total_price=float(row.get("total_price", 0)),
        created_at=row.get("created_at", ""),
        items=items,
    )

async def get_counterparties_by_phone(phone: str) -> list[E4Counterparty]:
    """GET /GetCounterpartys/PhoneNumber={phone} — поиск контрагента по номеру телефона."""
    async with _client() as c:
        resp = await c.get(f"GetCounterpartys/PhoneNumber={phone}")
        resp.raise_for_status()
        data = resp.json()
    rows = data if isinstance(data, list) else data.get("РезультатВыгрузки", [])
    return [
        E4Counterparty(
            e4_guid=row["guid"],    # TODO: уточнить имя поля
            name=row["name"],       # TODO: уточнить имя поля
            phone=phone,
        )
        for row in rows
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
