"""Orders router — all data comes from 1C via e4_service."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException

from app.e4_service import (
    E4Order,
    cancel_order as e4_cancel_order,
    create_order as e4_create_order,
    get_order,
    get_orders,
    get_product_matrix,
    update_order as e4_update_order,
)
from app.routers.counterparties import get_current_user
from app.schemas import OrderCreateIn, OrderItemOut, OrderOut, OrderUpdateIn

router = APIRouter(prefix="/api/orders", tags=["orders"])

_FULL_EDIT_STAGES = {"Заказано"}
_QTY_EDIT_STAGES = {"Зарезервировано"}


def _can_edit(stage: str) -> bool:
    return stage in _FULL_EDIT_STAGES | _QTY_EDIT_STAGES


def _order_to_out(order: E4Order) -> OrderOut:
    items = [OrderItemOut(**asdict(i)) for i in order.items]
    return OrderOut(
        e4_guid=order.e4_guid,
        counterparty_guid=order.counterparty_guid,
        delivery_point_guid=order.delivery_point_guid,
        delivery_date=order.delivery_date,
        status=order.status,
        stage=order.stage,
        total_price=order.total_price,
        created_at=order.created_at,
        items=items,
    )


@router.get("/", response_model=list[OrderOut])
async def list_orders(
    counterparty_guid: str,
    user: dict = Depends(get_current_user),
):
    orders = await get_orders(counterparty_guid)
    return [_order_to_out(o) for o in orders]


@router.get("/{e4_guid}", response_model=OrderOut)
async def get_order_detail(
    e4_guid: str,
    user: dict = Depends(get_current_user),
):
    order = await get_order(e4_guid)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return _order_to_out(order)


@router.post("/", response_model=OrderOut)
async def create_order_endpoint(
    body: OrderCreateIn,
    user: dict = Depends(get_current_user),
):
    products = await get_product_matrix(body.counterparty_guid)
    product_map = {p.e4_guid: p for p in products}

    items: list[dict] = []
    for item in body.items:
        p = product_map.get(item.product_guid)
        if not p:
            raise HTTPException(
                status_code=400,
                detail=f"Товар {item.product_guid} не найден в матрице",
            )
        items.append({
            "product_guid": p.e4_guid,
            "product_name": p.name,
            "quantity": item.quantity,
            "price": p.price,
            "box_multiplicity": p.box_multiplicity,
            "net_weight": p.net_weight,
            "gross_weight": p.gross_weight,
        })

    e4_guid = await e4_create_order({
        "counterparty_guid": body.counterparty_guid,
        "delivery_point_guid": body.delivery_point_guid,
        "delivery_date": str(body.delivery_date),
        "items": items,
    })

    order = await get_order(e4_guid)
    if not order:
        raise HTTPException(status_code=500, detail="Заказ создан в 1С, но не удалось получить данные")
    return _order_to_out(order)


@router.put("/{e4_guid}", response_model=OrderOut)
async def update_order_endpoint(
    e4_guid: str,
    body: OrderUpdateIn,
    user: dict = Depends(get_current_user),
):
    order = await get_order(e4_guid)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    if not _can_edit(order.stage):
        raise HTTPException(status_code=403, detail="Заказ недоступен для редактирования")

    is_full_edit = order.stage in _FULL_EDIT_STAGES

    if not is_full_edit and (body.delivery_point_guid or body.delivery_date):
        raise HTTPException(
            status_code=403,
            detail="На этапе 'Зарезервировано' можно изменять только количество товаров",
        )

    items_data: list[dict] | None = None
    if body.items is not None:
        products = await get_product_matrix(order.counterparty_guid)
        product_map = {p.e4_guid: p for p in products}
        items_data = []
        for item in body.items:
            p = product_map.get(item.product_guid)
            if not p:
                raise HTTPException(
                    status_code=400,
                    detail=f"Товар {item.product_guid} не найден в матрице",
                )
            items_data.append({
                "product_guid": p.e4_guid,
                "product_name": p.name,
                "quantity": item.quantity,
                "price": p.price,
                "box_multiplicity": p.box_multiplicity,
                "net_weight": p.net_weight,
                "gross_weight": p.gross_weight,
            })

    await e4_update_order(e4_guid, {
        "delivery_point_guid": body.delivery_point_guid if is_full_edit else None,
        "delivery_date": str(body.delivery_date) if body.delivery_date and is_full_edit else None,
        "items": items_data,
    })

    updated = await get_order(e4_guid)
    return _order_to_out(updated)


@router.post("/{e4_guid}/cancel", response_model=OrderOut)
async def cancel_order_endpoint(
    e4_guid: str,
    user: dict = Depends(get_current_user),
):
    order = await get_order(e4_guid)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    if not _can_edit(order.stage):
        raise HTTPException(status_code=403, detail="Заказ нельзя отменить на текущем этапе")

    await e4_cancel_order(e4_guid)

    updated = await get_order(e4_guid)
    return _order_to_out(updated)
