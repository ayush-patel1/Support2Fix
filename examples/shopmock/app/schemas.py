import uuid

from pydantic import BaseModel

from app.models import OrderStatus, PaymentStatus


class ProductPublic(BaseModel):
    id: uuid.UUID
    name: str
    price_cents: int

    model_config = {"from_attributes": True}


class CheckoutRequest(BaseModel):
    user_email: str
    subtotal_cents: int
    coupon_code: str | None = None


class PaymentPublic(BaseModel):
    payment_intent_id: str | None
    status: PaymentStatus
    attempts: int

    model_config = {"from_attributes": True}


class OrderPublic(BaseModel):
    id: uuid.UUID
    subtotal_cents: int
    coupon_code: str | None
    total_cents: int
    status: OrderStatus
    payment: PaymentPublic | None

    model_config = {"from_attributes": True}
