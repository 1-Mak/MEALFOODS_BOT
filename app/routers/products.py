"""Products router — matrix for a counterparty."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.e4_service import get_product_matrix
from app.routers.counterparties import get_current_user
from app.schemas import ProductOut

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("/", response_model=list[ProductOut])
async def list_products(
    counterparty_guid: str,
    user: dict = Depends(get_current_user),
):
    products = await get_product_matrix(counterparty_guid)
    return [
        ProductOut(
            e4_guid=p.e4_guid,
            name=p.name,
            unit=p.unit,
            box_multiplicity=p.box_multiplicity,
            net_weight=p.net_weight,
            gross_weight=p.gross_weight,
            price=p.price,
            vat_rate=p.vat_rate,
        )
        for p in products
    ]
