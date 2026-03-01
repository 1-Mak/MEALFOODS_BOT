"""Orders router — placeholder for Этап 4-6."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("/")
async def list_orders():
    return {"detail": "Not implemented yet (Этап 4)"}


@router.post("/")
async def create_order():
    return {"detail": "Not implemented yet (Этап 5)"}


@router.get("/{order_id}")
async def get_order(order_id: int):
    return {"detail": "Not implemented yet (Этап 4)"}


@router.put("/{order_id}")
async def update_order(order_id: int):
    return {"detail": "Not implemented yet (Этап 6)"}


@router.post("/{order_id}/cancel")
async def cancel_order(order_id: int):
    return {"detail": "Not implemented yet (Этап 6)"}
