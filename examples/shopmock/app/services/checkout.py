"""Cart -> order, with an optional coupon applied. Correct code — the bug

lives entirely in payment_service.py, not here; this just produces the
zero-total order that triggers it.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Coupon, Order, OrderStatus, Payment


class CheckoutError(Exception):
    pass


class CheckoutService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_order(
        self, *, user_id: uuid.UUID, subtotal_cents: int, coupon_code: str | None
    ) -> Order:
        discount_cents = 0
        if coupon_code:
            coupon = await self.db.get(Coupon, coupon_code)
            if coupon is None or not coupon.active:
                raise CheckoutError(f"Coupon {coupon_code!r} is not valid.")
            discount_cents = subtotal_cents * coupon.percent_off // 100

        total_cents = max(subtotal_cents - discount_cents, 0)

        order = Order(
            user_id=user_id,
            subtotal_cents=subtotal_cents,
            coupon_code=coupon_code,
            total_cents=total_cents,
            status=OrderStatus.PENDING,
        )
        self.db.add(order)
        await self.db.flush()

        payment = Payment(order_id=order.id)
        self.db.add(payment)
        await self.db.flush()
        order.payment = payment

        return order

    @staticmethod
    async def get_coupon(db: AsyncSession, code: str) -> Coupon | None:
        return (await db.execute(select(Coupon).where(Coupon.code == code))).scalar_one_or_none()
