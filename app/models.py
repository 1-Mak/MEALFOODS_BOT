from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OrderStatus(str, enum.Enum):
    draft = "draft"
    confirmed = "confirmed"
    in_processing = "in_processing"
    delivered = "delivered"
    cancelled = "cancelled"


# ------------------------------------------------------------------
# Users (MAX messenger users)
# ------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    max_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32))
    current_counterparty_id: Mapped[int | None] = mapped_column(
        ForeignKey("counterparties.id"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )

    current_counterparty: Mapped[Counterparty | None] = relationship(
        back_populates="users",
    )


# ------------------------------------------------------------------
# Counterparties (from 1C E4)
# ------------------------------------------------------------------

class Counterparty(Base):
    __tablename__ = "counterparties"

    id: Mapped[int] = mapped_column(primary_key=True)
    e4_guid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(512))
    phone: Mapped[str | None] = mapped_column(String(32), index=True)

    users: Mapped[list[User]] = relationship(back_populates="current_counterparty")
    delivery_points: Mapped[list[DeliveryPoint]] = relationship(
        back_populates="counterparty",
    )
    orders: Mapped[list[Order]] = relationship(back_populates="counterparty")


# ------------------------------------------------------------------
# Delivery points
# ------------------------------------------------------------------

class DeliveryPoint(Base):
    __tablename__ = "delivery_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    e4_guid: Mapped[str] = mapped_column(String(64), unique=True)
    counterparty_id: Mapped[int] = mapped_column(ForeignKey("counterparties.id"))
    address: Mapped[str] = mapped_column(String(1024))

    counterparty: Mapped[Counterparty] = relationship(
        back_populates="delivery_points",
    )


# ------------------------------------------------------------------
# Products (nomenclature)
# ------------------------------------------------------------------

class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    e4_guid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(512))
    unit: Mapped[str] = mapped_column(String(32), default="шт")
    box_multiplicity: Mapped[int] = mapped_column(default=1)
    net_weight: Mapped[float] = mapped_column(Numeric(10, 3), default=0)
    gross_weight: Mapped[float] = mapped_column(Numeric(10, 3), default=0)


# ------------------------------------------------------------------
# Product prices (per counterparty)
# ------------------------------------------------------------------

class ProductPrice(Base):
    __tablename__ = "product_prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    counterparty_id: Mapped[int] = mapped_column(ForeignKey("counterparties.id"))
    price: Mapped[float] = mapped_column(Numeric(12, 2))
    vat_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)

    product: Mapped[Product] = relationship()
    counterparty: Mapped[Counterparty] = relationship()


# ------------------------------------------------------------------
# Client product matrix (which products are available to a counterparty)
# ------------------------------------------------------------------

class ClientProductMatrix(Base):
    __tablename__ = "client_product_matrix"

    id: Mapped[int] = mapped_column(primary_key=True)
    counterparty_id: Mapped[int] = mapped_column(ForeignKey("counterparties.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))

    product: Mapped[Product] = relationship()
    counterparty: Mapped[Counterparty] = relationship()


# ------------------------------------------------------------------
# Orders
# ------------------------------------------------------------------

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    counterparty_id: Mapped[int] = mapped_column(ForeignKey("counterparties.id"))
    delivery_point_id: Mapped[int | None] = mapped_column(
        ForeignKey("delivery_points.id"),
    )
    delivery_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.draft,
    )
    total_price: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    total_net_weight: Mapped[float] = mapped_column(Numeric(10, 3), default=0)
    total_gross_weight: Mapped[float] = mapped_column(Numeric(10, 3), default=0)
    total_boxes: Mapped[int] = mapped_column(default=0)
    total_pallets: Mapped[int] = mapped_column(default=0)
    e4_order_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    counterparty: Mapped[Counterparty] = relationship(back_populates="orders")
    delivery_point: Mapped[DeliveryPoint | None] = relationship()
    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order", cascade="all, delete-orphan",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(default=1)
    price: Mapped[float] = mapped_column(Numeric(12, 2))
    amount: Mapped[float] = mapped_column(Numeric(14, 2))

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()
