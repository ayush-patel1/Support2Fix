"""Process payments for orders, including orders with no amount due."""

from app.models import Order, Payment, PaymentStatus
from app.services.payment_gateway import FakePaymentGateway


class PaymentRetryExhausted(Exception):
    pass


class PaymentService:
    MAX_RETRIES = 50

    def __init__(self, gateway: FakePaymentGateway | None = None) -> None:
        self.gateway = gateway or FakePaymentGateway()

    def process_order(self, order: Order, payment: Payment) -> Payment:
        if order.total_cents <= 0:
            payment.payment_intent_id = None
            payment.status = PaymentStatus.COMPLETED
            payment.attempts = 0
            return payment

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
