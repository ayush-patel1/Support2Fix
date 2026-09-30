"""A fake payment gateway — stands in for Stripe/etc. so the mock shop has

no real external dependency. `create_intent` is the one call
PaymentService is supposed to guard against a zero-dollar order and
doesn't — see payment_service.py.
"""

import uuid
from collections import defaultdict


class PaymentGatewayError(Exception):
    pass


class FakePaymentGateway:
    """A normal (non-null) intent "settles" — `poll` starts returning True —

    after `settles_after_polls` polls, simulating a real gateway's async
    confirmation. A `None` intent_id has nothing to poll and never settles.
    """

    def __init__(self, settles_after_polls: int = 2) -> None:
        self.settles_after_polls = settles_after_polls
        self._poll_counts: dict[str, int] = defaultdict(int)

    def create_intent(self, amount_cents: int) -> str:
        if amount_cents <= 0:
            raise PaymentGatewayError("Cannot create a payment intent for a zero-dollar amount.")
        return f"pi_{uuid.uuid4().hex[:16]}"

    def poll(self, intent_id: str | None) -> bool:
        if intent_id is None:
            return False
        self._poll_counts[intent_id] += 1
        return self._poll_counts[intent_id] >= self.settles_after_polls
