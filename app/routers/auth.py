"""Auth router — validate initData, issue JWT."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.auth import create_jwt, extract_user_id, validate_init_data
from app.database import get_user_by_max_id, upsert_user
from app.e4_service import get_counterparties_by_phone
from app.schemas import AuthRequest, AuthResponse, CounterpartyOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/validate", response_model=AuthResponse)
async def validate(body: AuthRequest):
    """Validate MAX Bridge initData and return JWT + counterparties."""
    data = validate_init_data(body.init_data)
    if data is None:
        raise HTTPException(status_code=401, detail="Invalid initData signature")

    user_id = extract_user_id(data)
    if not user_id:
        raise HTTPException(status_code=400, detail="No user_id in initData")

    # User must be registered (shared phone via bot)
    user = await get_user_by_max_id(user_id)
    if not user or not user.get("phone"):
        raise HTTPException(
            status_code=403,
            detail="Пользователь не зарегистрирован. Поделитесь номером телефона в чате с ботом.",
        )

    # Get counterparties for this phone
    counterparties = await get_counterparties_by_phone(user["phone"])

    token = create_jwt(user_id)

    return AuthResponse(
        token=token,
        user_id=user_id,
        counterparties=[
            CounterpartyOut(e4_guid=cp.e4_guid, name=cp.name)
            for cp in counterparties
        ],
    )


@router.post("/dev", response_model=AuthResponse)
async def dev_auth():
    """Dev-only: auth with a test user (phone +79200585280).

    Works only when a user with this phone exists in DB.
    Remove this endpoint before production.
    """
    test_phone = "88005553535"
    test_user_id = 1

    # Ensure test user exists
    await upsert_user(max_user_id=test_user_id, phone=test_phone)

    counterparties = await get_counterparties_by_phone(test_phone)
    token = create_jwt(test_user_id)

    return AuthResponse(
        token=token,
        user_id=test_user_id,
        counterparties=[
            CounterpartyOut(e4_guid=cp.e4_guid, name=cp.name)
            for cp in counterparties
        ],
    )
