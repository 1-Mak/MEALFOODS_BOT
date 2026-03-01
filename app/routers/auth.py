"""Auth router — placeholder for Этап 2."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/validate")
async def validate():
    return {"detail": "Not implemented yet (Этап 2)"}
