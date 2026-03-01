"""Products router — placeholder for Этап 5."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("/")
async def list_products():
    return {"detail": "Not implemented yet (Этап 5)"}
