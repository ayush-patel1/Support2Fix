"""Regression coverage for coupon checkout and payment processing."""

from app.models import Order, Payment, PaymentStatus
from app.services.payment_service import PaymentService


def test_zero_dollar_order_from_coupon_completes_without_hanging() -> None:
    """A fully discounted order completes without creating or polling an intent."""
    order = Order(subtotal_cents=8000, coupon_code="SAVE100", total_cents=0)
    payment = Payment()
    order.payment = payment

    result = PaymentService().process_order(order, payment)

    assert result.status == PaymentStatus.COMPLETED
    assert result.payment_intent_id is None
    assert result.attempts == 0


def test_full_price_order_completes_normally() -> None:
    """A normal, non-zero order creates an intent and completes."""
    order = Order(subtotal_cents=8000, coupon_code=None, total_cents=8000)
    payment = Payment()
    order.payment = payment

    result = PaymentService().process_order(order, payment)

    assert result.status == PaymentStatus.COMPLETED
    assert result.payment_intent_id is not None


def test_ten_percent_coupon_still_charges_and_completes() -> None:
    """A partial discount leaves a positive total that is charged normally."""
    order = Order(subtotal_cents=8000, coupon_code="SAVE10", total_cents=7200)
    payment = Payment()
    order.payment = payment

    result = PaymentService().process_order(order, payment)

    assert result.status == PaymentStatus.COMPLETED
    assert result.payment_intent_id is not None
