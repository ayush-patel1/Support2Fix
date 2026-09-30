"""THE BUG LIVES HERE. This is the real target of Support2Fix's first demo

scenario (see docs/architecture/system-design.md §3 and the investigation
console preview at /investigations/[id]).

Root cause: when a coupon zeroes an order's total, `process_order` never
creates a payment intent (there's nothing to charge), so
`payment.payment_intent_id` stays `None` — but the retry loop below has no
special case for that and polls a nonexistent intent forever. It only ever
stops because of the hardcoded `MAX_RETRIES` safety cap added here
specifically so a demo run fails fast instead of hanging the process; a
real, unpatched version of this bug wouldn't have that cap at all.

This is left broken on purpose — Phase 5's job is to hand later phases
(11-14: code investigation, reproduction, fix generation, validation) a
real bug to find and fix, not to fix it now. The intended fix is documented
in the module docstring of test_checkout_coupon.py, matching exactly what
the investigation console's "SYNTHESIZED AUTONOMOUS PATCH" panel already
shows.
"""

from app.models import Order, Payment, PaymentStatus
from app.services.payment_gateway import FakePaymentGateway


class PaymentRetryExhausted(Exception):
    pass


class PaymentService:
    MAX_RETRIES = 50

    def __init__(self, gateway: FakePaymentGateway | None = None) -> None:
        self.gateway = gateway or FakePaymentGateway()

    def process_order(self, order: Order, payment: Payment) -> Payment:
        # BUG: no branch for `order.total_cents <= 0`. A discount that
        # zeroes the total (SAVE100 on a full-price cart) skips straight to
        # the retry loop with `payment_intent_id` still `None`.
        if order.total_cents > 0:
            payment.payment_intent_id = self.gateway.create_intent(order.total_cents)

        attempt = 0
        while not self.gateway.poll(payment.payment_intent_id):
            payment.attempts = attempt
            attempt += 1
            if attempt >= self.MAX_RETRIES:
                payment.status = PaymentStatus.FAILED
                raise PaymentRetryExhausted(
                    f"PaymentService retry loop exceeded safety threshold: "
                    f"{self.MAX_RETRIES} iterations reached without state resolution."
                )

        payment.status = PaymentStatus.COMPLETED
        payment.attempts = attempt
        return payment
