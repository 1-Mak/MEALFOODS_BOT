from __future__ import annotations

from datetime import date

from pydantic import BaseModel


# ------------------------------------------------------------------
# Counterparty (from 1C via e4_service)
# ------------------------------------------------------------------

class CounterpartyOut(BaseModel):
    e4_guid: str
    name: str


# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------

class AuthRequest(BaseModel):
    init_data: str


class AuthResponse(BaseModel):
    token: str
    user_id: int
    counterparties: list[CounterpartyOut]


# ------------------------------------------------------------------
# Delivery point (from 1C via e4_service)
# ------------------------------------------------------------------

class DeliveryPointOut(BaseModel):
    e4_guid: str
    address: str


# ------------------------------------------------------------------
# Product (from 1C via e4_service)
# ------------------------------------------------------------------

class ProductOut(BaseModel):
    e4_guid: str
    name: str
    unit: str
    box_multiplicity: int
    net_weight: float
    gross_weight: float
    price: float
    vat_rate: float


# ------------------------------------------------------------------
# Order (sent to 1C via e4_service)
# ------------------------------------------------------------------

class OrderItemIn(BaseModel):
    product_guid: str
    quantity: int


class OrderCreateIn(BaseModel):
    counterparty_guid: str
    delivery_point_guid: str
    delivery_date: date
    items: list[OrderItemIn]


class OrderUpdateIn(BaseModel):
    delivery_point_guid: str | None = None
    delivery_date: date | None = None
    items: list[OrderItemIn] | None = None


# ------------------------------------------------------------------
# Order output
# ------------------------------------------------------------------

class OrderItemOut(BaseModel):
    id: int
    product_guid: str
    product_name: str
    quantity: int
    price: float
    box_multiplicity: int
    net_weight: float
    gross_weight: float


class OrderOut(BaseModel):
    id: int
    e4_guid: str | None
    counterparty_guid: str
    delivery_point_guid: str
    delivery_date: str
    status: str
    stage: str
    total_price: float
    created_at: str
    items: list[OrderItemOut] = []
