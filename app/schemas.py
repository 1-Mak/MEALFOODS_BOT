from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from app.models import OrderStatus


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
# Counterparty
# ------------------------------------------------------------------

class CounterpartyOut(BaseModel):
    id: int
    e4_guid: str
    name: str

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------
# Delivery point
# ------------------------------------------------------------------

class DeliveryPointOut(BaseModel):
    id: int
    e4_guid: str
    address: str

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------
# Product
# ------------------------------------------------------------------

class ProductOut(BaseModel):
    id: int
    e4_guid: str
    name: str
    unit: str
    box_multiplicity: int
    net_weight: float
    gross_weight: float
    price: float
    vat_rate: float

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------
# Order
# ------------------------------------------------------------------

class OrderItemIn(BaseModel):
    product_id: int
    quantity: int


class OrderCreateIn(BaseModel):
    counterparty_id: int
    delivery_point_id: int
    delivery_date: date
    items: list[OrderItemIn]


class OrderUpdateIn(BaseModel):
    delivery_point_id: int | None = None
    delivery_date: date | None = None
    items: list[OrderItemIn] | None = None


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    quantity: int
    price: float
    amount: float

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: int
    counterparty_id: int
    delivery_point_id: int | None
    delivery_date: date | None
    status: OrderStatus
    total_price: float
    total_net_weight: float
    total_gross_weight: float
    total_boxes: int
    total_pallets: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderDetailOut(OrderOut):
    items: list[OrderItemOut]
    delivery_point_address: str | None = None
