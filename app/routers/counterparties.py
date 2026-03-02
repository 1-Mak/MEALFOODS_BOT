"""Counterparties router — list counterparties for authenticated user."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException

from app.auth import decode_jwt
from app.database import get_user_by_max_id
from app.e4_service import get_counterparties_by_phone, get_delivery_points
from app.schemas import CounterpartyOut, DeliveryPointOut

router = APIRouter(prefix="/api/counterparties", tags=["counterparties"])


async def get_current_user(authorization: str = Header()) -> dict:
    """Extract and validate JWT from Authorization header."""
    token = authorization.replace("Bearer ", "")
    payload = decode_jwt(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = int(payload["sub"])
    user = await get_user_by_max_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.get("/", response_model=list[CounterpartyOut])
async def list_counterparties(user: dict = Depends(get_current_user)):
    """Return counterparties linked to the current user's phone."""
    phone = user.get("phone")
    if not phone:
        raise HTTPException(status_code=403, detail="Phone not registered")

    counterparties = await get_counterparties_by_phone(phone)
    return [
        CounterpartyOut(e4_guid=cp.e4_guid, name=cp.name)
        for cp in counterparties
    ]


@router.get("/{counterparty_guid}/delivery-points", response_model=list[DeliveryPointOut])
async def list_delivery_points(
    counterparty_guid: str,
    user: dict = Depends(get_current_user),
):
    """Return delivery points for a counterparty."""
    points = await get_delivery_points(counterparty_guid)
    return [
        DeliveryPointOut(e4_guid=dp.e4_guid, address=dp.address)
        for dp in points
    ]
