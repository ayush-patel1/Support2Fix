"""Shopmock: the Phase 5 target app. Run with:

    uvicorn app.main:app --reload --port 9000

This is a fixture for Support2Fix to eventually investigate, not part of
the platform — see examples/shopmock/README.md.
"""

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import Product, User
from app.schemas import CheckoutRequest, OrderPublic, ProductPublic
from app.services.checkout import CheckoutError, CheckoutService
from app.services.payment_service import PaymentRetryExhausted, PaymentService

app = FastAPI(title="Shopmock", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/products", response_model=list[ProductPublic])
async def list_products(db: AsyncSession = Depends(get_db)) -> list[Product]:
    return list((await db.execute(select(Product))).scalars().all())


@app.post("/checkout", response_model=OrderPublic)
async def checkout(body: CheckoutRequest, db: AsyncSession = Depends(get_db)) -> OrderPublic:
    """Creates an order from a subtotal + optional coupon, then processes

    payment synchronously. A coupon that zeroes the total (SAVE100 on a
    cart at or under the discount) will hang in PaymentService's retry loop
    until it hits the safety cap and this returns 500 — that's the bug,
    left in place on purpose. See payment_service.py.
    """
    stmt = select(User).where(User.email == body.user_email)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise HTTPException(404, f"No user with email {body.user_email!r}.")

    try:
        order = await CheckoutService(db).create_order(
            user_id=user.id, subtotal_cents=body.subtotal_cents, coupon_code=body.coupon_code
        )
    except CheckoutError as exc:
        raise HTTPException(422, str(exc)) from exc

    assert order.payment is not None
    try:
        PaymentService().process_order(order, order.payment)
    except PaymentRetryExhausted as exc:
        await db.commit()
        raise HTTPException(500, str(exc)) from exc

    await db.commit()
    return OrderPublic.model_validate(order)
