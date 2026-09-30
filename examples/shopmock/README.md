# shopmock

A small, real, deliberately-buggy e-commerce app — Phase 5's mock
production environment. This is not part of the Support2Fix platform; it's
a **target** the platform will eventually investigate, the same way it
would investigate any customer's app. See
[docs/architecture/system-design.md §3](../../docs/architecture/system-design.md)
and [§5](../../docs/architecture/system-design.md) for how this fits the
overall roadmap.

## The bug

A coupon that discounts an order to exactly $0 (`SAVE100`, 100% off) leaves
`PaymentService.process_order` polling a payment intent that was never
created — nothing to charge, so no intent, but the retry loop has no
branch for that case. It spins until a hardcoded safety cap
(`MAX_RETRIES = 50`) raises `PaymentRetryExhausted`. Full narrative,
root cause and the intended fix: `app/services/payment_service.py` and
`tests/test_checkout_coupon.py`'s docstrings.

This is the same scenario the investigation console preview
(`apps/web/app/investigations/[id]`) already dramatizes — this app is
what makes that scenario real instead of illustrative static text.

**This repo has its own git history** (a real, separate `.git`, gitignored
by the outer project repo) with the actual regression commit:

```bash
git log --oneline
git show 44f7845   # "Optimize coupon validation" — introduces the bug
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
reproduces the bug (500, `PaymentRetryExhausted`). Drop `coupon_code` or use
`SAVE10` and it completes normally.

## Testing

```bash
./.venv/Scripts/python -m pytest -v
```

**One test is expected to fail** —
`test_zero_dollar_order_from_coupon_completes_without_hanging`. That
failure *is* the reproduction (`1 failed, 2 passed, 3 total`, matching the
investigation console preview exactly). This is deliberate; don't "fix" it
by loosening the assertion. It's excluded from the main platform's own
`apps/api` test run by simply being a separate Python project — no special
CI carve-out needed.

## Fixtures

- `logs/application.jsonl` — the incident's log lines (deploy, checkout
  request, the zero-total order, the retry-exhausted error), timestamped
  to match the investigation console preview's timeline.
- `data/deployments.json` — the `v2.8.1` deployment record, with the real
  commit hash of the regression.

Regenerate both (and reseed the database) with `python -m app.seed`.

## What's deliberately not here yet

Only the coupon/zero-total bug is fully built out, per the original
spec's "the first complete scenario should be the coupon checkout bug."
Four more example bug categories are documented in the platform's
top-level task spec (a DB field type change, a renamed API field, an
auth-token expiry bug, and an infinite payment-retry-on-a-different-cause
bug) but aren't implemented here — that's future work, not scoped into
Phase 5 as delivered.
