# shopmock

A small e-commerce app — Phase 5's mock production environment. This is not
part of the Support2Fix platform; it's a **target** the platform can
investigate, the same way it would investigate any customer's app. See
[docs/architecture/system-design.md §3](../../docs/architecture/system-design.md)
and [§5](../../docs/architecture/system-design.md) for how this fits the
overall roadmap.

## The checkout regression

A historical regression made `PaymentService.process_order` poll an intent
that was never created when a coupon reduced an order to exactly $0.
Payment processing now completes such orders immediately without creating
or polling an intent. Regression tests cover this behavior alongside normal
and partially discounted orders.

Support2Fix's investigation worker reads the checked-in source, deployment,
and historical log fixtures through the local integration adapters. It
reports a source-matched hypothesis, not a confirmed root cause.

The app lives in the main Support2Fix Git repository rather than a nested
repository. The Phase 5 commit that introduced the target implementation is:

```bash
git log --oneline -- examples/shopmock
git show 224f8a8:examples/shopmock/app/services/payment_service.py
```

## Running it

```bash
python -m venv .venv
./.venv/Scripts/pip install -e ".[dev]"     # macOS/Linux: source .venv/bin/activate first

# Postgres, once — a separate database from the platform's own:
#   CREATE DATABASE shopmock OWNER support2fix;

SHOPMOCK_DATABASE_URL=postgresql+asyncpg://support2fix:support2fix@localhost:5432/shopmock \
  ./.venv/Scripts/python -m app.seed   # creates schema + seeds products/coupons/a customer

./.venv/Scripts/python -m uvicorn app.main:app --reload --port 9000
```

`POST /checkout` with `{"user_email": "jane.doe@acme-commerce.example", "subtotal_cents": 8000, "coupon_code": "SAVE100"}`
completes with no payment intent. Drop `coupon_code` or use `SAVE10` to
exercise a positive payment amount.

## Testing

```bash
./.venv/Scripts/python -m pytest -v
```

The checkout regression tests should all pass. They're excluded from the
main platform's own `apps/api` test run because this is a separate Python
project.

## Fixtures

- `logs/application.jsonl` — historical incident log lines, timestamped to
  match the historical deployment.
- `data/deployments.json` — the `v2.8.1` deployment record, with the real
  Support2Fix commit hash that introduced this target implementation.

Regenerate both (and reseed the database) with `python -m app.seed`.

## What's deliberately not here yet

Only the coupon/zero-total bug is fully built out, per the original
spec's "the first complete scenario should be the coupon checkout bug."
Four more example bug categories are documented in the platform's
top-level task spec (a DB field type change, a renamed API field, an
auth-token expiry bug, and an infinite payment-retry-on-a-different-cause
bug) but aren't implemented here — that's future work, not scoped into
Phase 5 as delivered.
