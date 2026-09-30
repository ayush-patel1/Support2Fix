"""The Phase 5 demo scenario's reproduction case.

`test_zero_dollar_order_from_coupon_completes_without_hanging` is EXPECTED
TO FAIL against the current code — that failure IS the reproduction. Later
phases (11-14: code investigation, reproduction, fix generation,
validation) will find this exact failure, generate a fix, and this test
should then pass. Don't "fix" it here by loosening the assertion; that
would defeat the point of Phase 5.

Root cause: SAVE100 zeroes the order total. PaymentService never creates a
payment intent for a $0 order (nothing to charge), but its retry loop has
no branch for that case either, so it polls a `None` intent forever until
the hardcoded safety cap raises PaymentRetryExhausted.

The intended fix (for a future phase to generate and apply, not applied
here) is a zero-total short-circuit before the retry loop:

    if order.total_cents <= 0:
        payment.status = PaymentStatus.COMPLETED
        return payment
    if order.total_cents > 0:
        payment.payment_intent_id = self.gateway.create_intent(order.total_cents)
    ...

— matching exactly what the investigation console preview's "SYNTHESIZED
AUTONOMOUS PATCH" panel already shows (apps/web/app/investigations/[id]).
"""

from app.models import Order, Payment, PaymentStatus
from app.services.payment_service import PaymentService


def test_zero_dollar_order_from_coupon_completes_without_hanging() -> None:
    """A cart fully covered by a coupon (SAVE100 on an $80.00 subtotal)

    should complete instantly — there's nothing to charge. Currently
    raises PaymentRetryExhausted instead. THIS FAILURE IS THE BUG.
    """
    order = Order(subtotal_cents=8000, coupon_code="SAVE100", total_cents=0)
    payment = Payment()
    order.payment = payment

    result = PaymentService().process_order(order, payment)

    assert result.status == PaymentStatus.COMPLETED


def test_full_price_order_completes_normally() -> None:
    """Control case: a normal, non-zero order is NOT affected by this bug —

    proves the failure above is specific to the zero-total path, not a
    general breakage of checkout.
    """
    order = Order(subtotal_cents=8000, coupon_code=None, total_cents=8000)
    payment = Payment()
    order.payment = payment

    result = PaymentService().process_order(order, payment)

    assert result.status == PaymentStatus.COMPLETED
    assert result.payment_intent_id is not None


def test_ten_percent_coupon_still_charges_and_completes() -> None:
    """A partial discount (SAVE10) leaves a positive total — also

    unaffected by this bug, since it never hits the total_cents <= 0 path.
    """
    order = Order(subtotal_cents=8000, coupon_code="SAVE10", total_cents=7200)
    payment = Payment()
    order.payment = payment

    result = PaymentService().process_order(order, payment)

    assert result.status == PaymentStatus.COMPLETED
    assert result.payment_intent_id is not None
