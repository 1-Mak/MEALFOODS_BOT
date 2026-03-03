"""Orders router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.database import (
    cancel_order,
    create_order,
    get_order,
    get_orders,
    update_order,
)
from app.e4_service import create_order as e4_create_order
from app.e4_service import get_product_matrix
from app.routers.counterparties import get_current_user
from app.schemas import OrderCreateIn, OrderItemOut, OrderOut, OrderUpdateIn

router = APIRouter(prefix="/api/orders", tags=["orders"])

# Stages that allow full editing (date, address, composition)
_FULL_EDIT_STAGES = {"Заказано"}
# Stages that allow only quantity editing
_QTY_EDIT_STAGES = {"Зарезервировано"}


def _can_edit(stage: str) -> bool:
    return stage in _FULL_EDIT_STAGES | _QTY_EDIT_STAGES


def _order_to_out(order: dict) -> OrderOut:
    items = [OrderItemOut(**i) for i in order.get("items", [])]
    return OrderOut(
        id=order["id"],
        e4_guid=order.get("e4_guid"),
        counterparty_guid=order["counterparty_guid"],
        delivery_point_guid=order["delivery_point_guid"],
        delivery_date=order["delivery_date"],
        status=order["status"],
        stage=order["stage"],
        total_price=order["total_price"],
        created_at=order["created_at"],
        items=items,
    )


@router.get("/", response_model=list[OrderOut])
async def list_orders(
    counterparty_guid: str,
    user: dict = Depends(get_current_user),
):
    orders = await get_orders(counterparty_guid)
    result = []
    for o in orders:
        o["items"] = []
        result.append(_order_to_out(o))
    return result


@router.get("/{order_id}", response_model=OrderOut)
async def get_order_detail(
    order_id: int,
    user: dict = Depends(get_current_user),
):
    order = await get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return _order_to_out(order)


@router.post("/", response_model=OrderOut)
async def create_order_endpoint(
    body: OrderCreateIn,
    user: dict = Depends(get_current_user),
):
    # Enrich items with product info from e4_service
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

    # Send to E4, get guid back
    e4_guid = await e4_create_order({
        "counterparty_guid": body.counterparty_guid,
        "delivery_point_guid": body.delivery_point_guid,
        "delivery_date": str(body.delivery_date),
        "items": items,
    })

    order_id = await create_order(
        counterparty_guid=body.counterparty_guid,
        delivery_point_guid=body.delivery_point_guid,
        delivery_date=str(body.delivery_date),
        items=items,
        e4_guid=e4_guid,
    )

    order = await get_order(order_id)
    return _order_to_out(order)


@router.put("/{order_id}", response_model=OrderOut)
async def update_order_endpoint(
    order_id: int,
    body: OrderUpdateIn,
    user: dict = Depends(get_current_user),
):
    order = await get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    if not _can_edit(order["stage"]):
        raise HTTPException(status_code=403, detail="Заказ недоступен для редактирования")

    is_full_edit = order["stage"] in _FULL_EDIT_STAGES

    # On "Зарезервировано" only quantity changes allowed
    if not is_full_edit and (body.delivery_point_guid or body.delivery_date):
        raise HTTPException(
            status_code=403,
            detail="На этапе 'Зарезервировано' можно изменять только количество товаров",
        )

    items_data: list[dict] | None = None
    if body.items is not None:
        products = await get_product_matrix(order["counterparty_guid"])
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

    await update_order(
        order_id=order_id,
        delivery_point_guid=body.delivery_point_guid if is_full_edit else None,
        delivery_date=str(body.delivery_date) if body.delivery_date and is_full_edit else None,
        items=items_data,
    )

    updated = await get_order(order_id)
    return _order_to_out(updated)


@router.post("/{order_id}/cancel", response_model=OrderOut)
async def cancel_order_endpoint(
    order_id: int,
    user: dict = Depends(get_current_user),
):
    order = await get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    if not _can_edit(order["stage"]):
        raise HTTPException(status_code=403, detail="Заказ нельзя отменить на текущем этапе")

    await cancel_order(order_id)
    updated = await get_order(order_id)
    return _order_to_out(updated)
