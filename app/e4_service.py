"""Abstraction layer for 1C E4 data access.

When E4_HTTP_URL is set in .env  → delegates to e4_http_client (real 1C HTTP service).
When E4_HTTP_URL is empty        → falls back to mock data (for local dev/testing).

In HTTP mode, responses are cached in memory (see app/cache.py).
If 1C is temporarily unavailable, stale cache is returned as fallback.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from app import cache
from app.config import settings

logger = logging.getLogger(__name__)

# TTL в секундах
TTL_COUNTERPARTIES = 60 * 60   # 60 мин
TTL_DELIVERY_POINTS = 60 * 60  # 60 мин
TTL_PRODUCTS = 30 * 60         # 30 мин
TTL_ORDERS = 2 * 60            # 2 мин
TTL_ORDER = 60                 # 1 мин


# ------------------------------------------------------------------
# Data classes (internal representation, decoupled from HTTP/ORM)
# ------------------------------------------------------------------

@dataclass
class E4Counterparty:
    e4_guid: str
    name: str
    phone: str


@dataclass
class E4DeliveryPoint:
    e4_guid: str
    counterparty_guid: str
    address: str


@dataclass
class E4Product:
    e4_guid: str
    name: str
    unit: str
    box_multiplicity: int
    net_weight: float
    gross_weight: float
    price: float
    vat_rate: float


@dataclass
class E4OrderItem:
    product_guid: str
    product_name: str
    quantity: int
    price: float
    box_multiplicity: int
    net_weight: float
    gross_weight: float


@dataclass
class E4Order:
    e4_guid: str
    counterparty_guid: str
    delivery_point_guid: str
    delivery_date: str
    status: str
    stage: str
    total_price: float
    created_at: str
    items: list[E4OrderItem] = field(default_factory=list)


# ------------------------------------------------------------------
# Mock data (used when E4_HTTP_URL is not configured)
# ------------------------------------------------------------------

_COUNTERPARTIES = [
    E4Counterparty("guid-cp-001", "ООО Ромашка", "+79991234567"),
    E4Counterparty("guid-cp-002", "ООО Лютик", "+79991234567"),
    E4Counterparty("guid-cp-003", "ИП Иванов", "+79997654321"),
    E4Counterparty("guid-cp-004", "ИП Макаров", "+79200585280"),
    E4Counterparty("guid-cp-005", "ИП Субботина", "+79081511376"),
    E4Counterparty("guid-cp-006", "ИП Субботина", "+79202590557"),
    E4Counterparty("guid-cp-006", "ИП Субботина", "+79534731803"),
]

_DELIVERY_POINTS = [
    E4DeliveryPoint("guid-dp-001", "guid-cp-001", "г. Москва, ул. Ленина, д. 10"),
    E4DeliveryPoint("guid-dp-002", "guid-cp-001", "г. Москва, ул. Мира, д. 5"),
    E4DeliveryPoint("guid-dp-003", "guid-cp-002", "г. Казань, ул. Баумана, д. 3"),
    E4DeliveryPoint("guid-dp-004", "guid-cp-003", "г. Самара, ул. Победы, д. 7"),
    E4DeliveryPoint("guid-dp-005", "guid-cp-004", "г. Новосибирск, ул. Красный проспект, д. 1"),
    E4DeliveryPoint("guid-dp-006", "guid-cp-004", "г. Новосибирск, ул. Советская, д. 15"),
]

_PRODUCTS = [
    E4Product("guid-pr-001", "Котлета куриная 100г", "шт", 20, 0.100, 0.120, 45.00, 10.0),
    E4Product("guid-pr-002", "Сосиски Молочные 500г", "шт", 12, 0.500, 0.550, 120.00, 10.0),
    E4Product("guid-pr-003", "Колбаса Докторская 400г", "шт", 10, 0.400, 0.450, 210.00, 10.0),
    E4Product("guid-pr-004", "Пельмени Домашние 900г", "шт", 8, 0.900, 0.960, 180.00, 10.0),
    E4Product("guid-pr-005", "Фарш говяжий 500г", "шт", 15, 0.500, 0.540, 250.00, 10.0),
]

_MATRIX: dict[str, list[str]] = {
    "guid-cp-001": ["guid-pr-001", "guid-pr-002", "guid-pr-003", "guid-pr-004", "guid-pr-005"],
    "guid-cp-002": ["guid-pr-001", "guid-pr-003", "guid-pr-005"],
    "guid-cp-003": ["guid-pr-002", "guid-pr-004"],
    "guid-cp-004": ["guid-pr-001", "guid-pr-002", "guid-pr-003", "guid-pr-004", "guid-pr-005"],
    "guid-cp-005": ["guid-pr-001", "guid-pr-002", "guid-pr-003", "guid-pr-004", "guid-pr-005"],
    "guid-cp-006": ["guid-pr-001", "guid-pr-002", "guid-pr-003", "guid-pr-004", "guid-pr-005"],
}

_MOCK_ORDERS: list[E4Order] = [
    E4Order(
        e4_guid="guid-order-001",
        counterparty_guid="guid-cp-001",
        delivery_point_guid="guid-dp-001",
        delivery_date="2026-03-10",
        status="Резервируется",
        stage="Заказано",
        total_price=1350.00,
        created_at="2026-03-04T10:00:00",
        items=[
            E4OrderItem("guid-pr-001", "Котлета куриная 100г", 10, 45.00, 20, 0.100, 0.120),
            E4OrderItem("guid-pr-002", "Сосиски Молочные 500г", 5, 120.00, 12, 0.500, 0.550),
        ],
    ),
]


# ------------------------------------------------------------------
# Service methods — switch between mock and real HTTP
# ------------------------------------------------------------------

def _use_http() -> bool:
    return bool(settings.e4_http_url)


async def _cached_http(cache_key: str, ttl: float, http_call):
    """Fetch from cache or call 1C HTTP, with stale fallback on error."""
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        result = await http_call()
        cache.set(cache_key, result, ttl)
        return result
    except Exception as exc:
        stale = cache.get_stale(cache_key)
        if stale is not None:
            logger.warning("1C unavailable (%s), returning stale cache for %s", exc, cache_key)
            return stale
        raise


async def get_counterparties_by_phone(phone: str) -> list[E4Counterparty]:
    if _use_http():
        from app.e4_http_client import get_counterparties_by_phone as _http
        return await _cached_http(f"counterparties:{phone}", TTL_COUNTERPARTIES, lambda: _http(phone))
    normalized = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    return [cp for cp in _COUNTERPARTIES if cp.phone == normalized]


async def get_delivery_points(counterparty_guid: str) -> list[E4DeliveryPoint]:
    if _use_http():
        try:
            from app.e4_http_client import get_delivery_points as _http
            return await _cached_http(f"delivery_points:{counterparty_guid}", TTL_DELIVERY_POINTS, lambda: _http(counterparty_guid))
        except Exception:
            logger.warning("1C delivery_points not available, using mock data")
    return [dp for dp in _DELIVERY_POINTS if dp.counterparty_guid == counterparty_guid]


async def get_product_matrix(counterparty_guid: str) -> list[E4Product]:
    if _use_http():
        try:
            from app.e4_http_client import get_product_matrix as _http
            return await _cached_http(f"products:{counterparty_guid}", TTL_PRODUCTS, lambda: _http(counterparty_guid))
        except Exception:
            logger.warning("1C products not available, using mock data")
    product_guids = _MATRIX.get(counterparty_guid, [])
    return [p for p in _PRODUCTS if p.e4_guid in product_guids]


async def get_orders(counterparty_guid: str) -> list[E4Order]:
    if _use_http():
        try:
            from app.e4_http_client import get_orders as _http
            return await _cached_http(f"orders:{counterparty_guid}", TTL_ORDERS, lambda: _http(counterparty_guid))
        except Exception:
            logger.warning("1C orders not available, using mock data")
    return [o for o in _MOCK_ORDERS if o.counterparty_guid == counterparty_guid]


async def get_order(e4_guid: str) -> E4Order | None:
    if _use_http():
        try:
            from app.e4_http_client import get_order as _http
            return await _cached_http(f"order:{e4_guid}", TTL_ORDER, lambda: _http(e4_guid))
        except Exception:
            logger.warning("1C order not available, using mock data")
    return next((o for o in _MOCK_ORDERS if o.e4_guid == e4_guid), None)


async def create_order(order_data: dict) -> str:
    if _use_http():
        from app.e4_http_client import create_order as _http
        result = await _http(order_data)
        cache.invalidate(f"orders:{order_data.get('counterparty_guid', '')}")
        return result
    return f"guid-order-{uuid.uuid4().hex[:8]}"


async def update_order(order_guid: str, data: dict) -> str:
    if _use_http():
        from app.e4_http_client import update_order as _http
        result = await _http(order_guid, data)
        cache.invalidate(f"order:{order_guid}")
        cache.invalidate("orders:")
        return result
    return "updated"


async def cancel_order(order_guid: str) -> str:
    if _use_http():
        from app.e4_http_client import cancel_order as _http
        result = await _http(order_guid)
        cache.invalidate(f"order:{order_guid}")
        cache.invalidate("orders:")
        return result
    return "cancelled"
