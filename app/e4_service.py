"""Abstraction layer for 1C E4 data access.

Currently returns mock data. On Этап 7 the implementation will be
replaced with real OData v3 calls via odata_client.py — no other
code needs to change.
"""
from __future__ import annotations

from dataclasses import dataclass


# ------------------------------------------------------------------
# Data classes (internal representation, decoupled from ORM)
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


# ------------------------------------------------------------------
# Mock data
# ------------------------------------------------------------------

_COUNTERPARTIES = [
    E4Counterparty("guid-cp-001", "ООО Ромашка", "+79991234567"),
    E4Counterparty("guid-cp-002", "ООО Лютик", "+79991234567"),
    E4Counterparty("guid-cp-003", "ИП Иванов", "+79997654321"),
    E4Counterparty("guid-cp-003", "ИП Макаров", "+79200585280"),
    E4Counterparty("guid-cp-003", "ИП Субботина", "+79081511376"),
    E4Counterparty("guid-cp-003", "ИП Субботина", "+79202590557"),
]

_DELIVERY_POINTS = [
    E4DeliveryPoint("guid-dp-001", "guid-cp-001", "г. Москва, ул. Ленина, д. 10"),
    E4DeliveryPoint("guid-dp-002", "guid-cp-001", "г. Москва, ул. Мира, д. 5"),
    E4DeliveryPoint("guid-dp-003", "guid-cp-002", "г. Казань, ул. Баумана, д. 3"),
    E4DeliveryPoint("guid-dp-004", "guid-cp-003", "г. Самара, ул. Победы, д. 7"),
]

_PRODUCTS = [
    E4Product("guid-pr-001", "Котлета куриная 100г", "шт", 20, 0.100, 0.120, 45.00, 10.0),
    E4Product("guid-pr-002", "Сосиски Молочные 500г", "шт", 12, 0.500, 0.550, 120.00, 10.0),
    E4Product("guid-pr-003", "Колбаса Докторская 400г", "шт", 10, 0.400, 0.450, 210.00, 10.0),
    E4Product("guid-pr-004", "Пельмени Домашние 900г", "шт", 8, 0.900, 0.960, 180.00, 10.0),
    E4Product("guid-pr-005", "Фарш говяжий 500г", "шт", 15, 0.500, 0.540, 250.00, 10.0),
]

# Matrix: which products are available to which counterparty
_MATRIX: dict[str, list[str]] = {
    "guid-cp-001": ["guid-pr-001", "guid-pr-002", "guid-pr-003", "guid-pr-004", "guid-pr-005"],
    "guid-cp-002": ["guid-pr-001", "guid-pr-003", "guid-pr-005"],
    "guid-cp-003": ["guid-pr-002", "guid-pr-004"],
}


# ------------------------------------------------------------------
# Service methods (mock implementation)
# ------------------------------------------------------------------

async def get_counterparties_by_phone(phone: str) -> list[E4Counterparty]:
    """Find counterparties linked to a phone number."""
    normalized = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    return [cp for cp in _COUNTERPARTIES if cp.phone == normalized]


async def get_delivery_points(counterparty_guid: str) -> list[E4DeliveryPoint]:
    """Get delivery points for a counterparty."""
    return [dp for dp in _DELIVERY_POINTS if dp.counterparty_guid == counterparty_guid]


async def get_product_matrix(counterparty_guid: str) -> list[E4Product]:
    """Get available products with prices for a counterparty."""
    product_guids = _MATRIX.get(counterparty_guid, [])
    return [p for p in _PRODUCTS if p.e4_guid in product_guids]


async def create_order(order_data: dict) -> str:
    """Create an order in E4. Returns the E4 order GUID."""
    # Mock: just return a fake GUID
    import uuid
    return f"guid-order-{uuid.uuid4().hex[:8]}"


async def update_order(order_guid: str, data: dict) -> str:
    """Update an order in E4. Returns status."""
    return "updated"


async def cancel_order(order_guid: str) -> str:
    """Cancel an order in E4. Returns status."""
    return "cancelled"
