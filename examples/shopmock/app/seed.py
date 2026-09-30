"""Creates the schema and seeds shopmock's data: a customer, products, the

SAVE100 coupon, plus the generated log/deployment fixtures the eventual
Evidence Collection agent (Phase 9-10) will read. Run with:

    python -m app.seed
"""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app.core.db import Base, SessionLocal, engine
from app.models import Coupon, Product, User

FIXTURES_DIR = Path(__file__).resolve().parent.parent
LOGS_PATH = FIXTURES_DIR / "logs" / "application.jsonl"
DEPLOYMENTS_PATH = FIXTURES_DIR / "data" / "deployments.json"


async def seed_data() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        existing = (await db.execute(select(User))).scalars().first()
        if existing is not None:
            print("Already seeded — skipping. Drop the `shopmock` database to reseed from scratch.")
            return

        db.add(User(email="jane.doe@acme-commerce.example", name="Jane Doe"))
        db.add_all(
            [
                Product(name="Wireless Headphones", price_cents=8000),
                Product(name="Mechanical Keyboard", price_cents=12000),
                Product(name="USB-C Hub", price_cents=4500),
            ]
        )
        db.add(Coupon(code="SAVE100", percent_off=100, active=True))
        db.add(Coupon(code="SAVE10", percent_off=10, active=True))
        await db.commit()

    print("Seeded shopmock database.")


def write_fixtures() -> None:
    """Generates the log lines and deployment record for the coupon

    incident, matching the timeline already shown in the investigation
    console preview (app/investigations/[id] in apps/web) — deploy at
    14:21:04, client signal at 14:30:11, the error spike at 14:32:19.
    """
    deploy_time = datetime(2026, 9, 30, 14, 21, 4, tzinfo=UTC)

    deployments = [
        {
            "service": "shopmock",
            "version": "v2.8.1",
            "commit_sha": None,  # filled in by scripts/init_shopmock_repo.* after `git commit`
            "deployed_at": deploy_time.isoformat(),
            "status": "SUCCESS",
        }
    ]
    DEPLOYMENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEPLOYMENTS_PATH.write_text(json.dumps(deployments, indent=2) + "\n")

    logs = [
        {
            "timestamp": deploy_time.isoformat(),
            "level": "INFO",
            "service": "shopmock",
            "message": "Deployment v2.8.1 rolled out.",
        },
        {
            "timestamp": "2026-09-30T14:30:11+00:00",
            "level": "INFO",
            "service": "shopmock",
            "message": "Checkout request received: coupon=SAVE100 subtotal_cents=8000",
        },
        {
            "timestamp": "2026-09-30T14:30:11+00:00",
            "level": "INFO",
            "service": "shopmock",
            "message": "Order created: total_cents=0 (coupon zeroed the subtotal)",
        },
        {
            "timestamp": "2026-09-30T14:32:19+00:00",
            "level": "ERROR",
            "service": "shopmock",
            "message": (
                "PaymentRetryExhausted: PaymentService retry loop exceeded safety threshold: "
                "50 iterations reached without state resolution."
            ),
        },
    ]
    LOGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOGS_PATH.open("w") as f:
        for entry in logs:
            f.write(json.dumps(entry) + "\n")

    print(f"Wrote {DEPLOYMENTS_PATH} and {LOGS_PATH}.")


if __name__ == "__main__":
    asyncio.run(seed_data())
    write_fixtures()
