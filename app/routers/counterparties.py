"""Counterparties router — placeholder for Этап 2."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/counterparties", tags=["counterparties"])


@router.get("/")
async def list_counterparties():
    return {"detail": "Not implemented yet (Этап 2)"}
