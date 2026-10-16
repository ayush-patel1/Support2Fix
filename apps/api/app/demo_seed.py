"""Create an isolated local demo tenant and its shopmock incident.

Run with `DEMO_PASSWORD='a-local-only-password' python -m app.demo_seed`.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import get_settings
from app.core.db import dispose_engine, get_engine, init_engine
from app.core.security import hash_password
from app.models.customer import (
    CodeRepository,
    Customer,
    CustomerEnvironment,
    CustomerTier,
    RepositoryProvider,
    Service,
)
from app.models.integration import Integration, IntegrationKind, IntegrationProvider
from app.models.membership import Membership, Role
from app.models.organization import Organization
from app.models.ticket import Ticket, TicketEvent, TicketEventType, TicketPriority, TicketStatus
from app.models.user import User
from app.repositories.organizations import OrganizationRepository

DEMO_EMAIL = "demo@support2fix.example.com"
LEGACY_DEMO_EMAIL = "demo@support2fix.local"
DEMO_ORGANIZATION = "Support2Fix Demo"
DEMO_TICKET_TITLE = "Checkout fails after a zero-value coupon"


async def seed_demo() -> str:
    settings = get_settings()
    if settings.environment == "production":
        raise RuntimeError("Refusing to create demo data in production.")
    password = os.environ.get("DEMO_PASSWORD", "")
    if len(password) < 12:
        raise ValueError("Set DEMO_PASSWORD to a local password of at least 12 characters.")

    repository_root = Path(os.environ.get("DEMO_REPO_PATH", Path(__file__).resolve().parents[3]))
    shopmock = repository_root / "examples" / "shopmock"
    if not shopmock.is_dir():
        raise ValueError(f"shopmock directory not found at {shopmock}.")
    config_by_kind = {
        IntegrationKind.CODE_HOST: {"repo_path": str(shopmock)},
        IntegrationKind.LOG_SOURCE: {"log_path": str(shopmock / "logs" / "application.jsonl")},
        IntegrationKind.DEPLOYMENT_SOURCE: {
            "deployments_path": str(shopmock / "data" / "deployments.json")
        },
    }

    init_engine(settings.database_url, echo=settings.database_echo)
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    try:
        async with session_factory() as db:
            user = (
                await db.execute(select(User).where(User.email == DEMO_EMAIL))
            ).scalar_one_or_none()
            if user is None:
                user = (
                    await db.execute(select(User).where(User.email == LEGACY_DEMO_EMAIL))
                ).scalar_one_or_none()
                if user is not None:
                    user.email = DEMO_EMAIL
            if user is None:
                user = User(email=DEMO_EMAIL, password_hash=hash_password(password))
                db.add(user)
                await db.flush()
                organization = await OrganizationRepository(db).create(name=DEMO_ORGANIZATION)
                db.add(
                    Membership(
                        user_id=user.id,
                        organization_id=organization.id,
                        role=Role.ADMIN,
                    )
                )
                await db.flush()
            else:
                membership = (
                    await db.execute(
                        select(Membership).join(
                            Organization, Organization.id == Membership.organization_id
                        ).where(
                            Membership.user_id == user.id,
                            Membership.role == Role.ADMIN,
                            Organization.name == DEMO_ORGANIZATION,
                        )
                    )
                ).scalar_one_or_none()
                if membership is None:
                    raise ValueError(
                        f"{DEMO_EMAIL} exists but has no admin membership; refusing to modify it."
                    )
                existing_organization = await db.get(Organization, membership.organization_id)
                if existing_organization is None:
                    raise ValueError("The demo user's organization no longer exists.")
                organization = existing_organization

            customer = (
                await db.execute(
                    select(Customer).where(
                        Customer.organization_id == organization.id,
                        Customer.name == "Acme Commerce",
                    )
                )
            ).scalar_one_or_none()
            if customer is None:
                customer = Customer(
                    organization_id=organization.id,
                    name="Acme Commerce",
                    external_ref="acme-commerce",
                    tier=CustomerTier.STANDARD,
                )
                db.add(customer)
                await db.flush()

            environment = (
                await db.execute(
                    select(CustomerEnvironment).where(
                        CustomerEnvironment.organization_id == organization.id,
                        CustomerEnvironment.customer_id == customer.id,
                        CustomerEnvironment.name == "production",
                    )
                )
            ).scalar_one_or_none()
            if environment is None:
                environment = CustomerEnvironment(
                    organization_id=organization.id,
                    customer_id=customer.id,
                    name="production",
                )
                db.add(environment)
                await db.flush()

            service = (
                await db.execute(
                    select(Service).where(
                        Service.organization_id == organization.id,
                        Service.environment_id == environment.id,
                        Service.name == "shopmock-checkout",
                    )
                )
            ).scalar_one_or_none()
            if service is None:
                service = Service(
                    organization_id=organization.id,
                    environment_id=environment.id,
                    name="shopmock-checkout",
                    language="Python",
                    owner_team="Commerce",
                )
                db.add(service)
                await db.flush()
                db.add(
                    CodeRepository(
                        organization_id=organization.id,
                        service_id=service.id,
                        provider=RepositoryProvider.LOCAL,
                        full_name="examples/shopmock",
                        default_branch="main",
                    )
                )

            ticket = (
                await db.execute(
                    select(Ticket).where(
                        Ticket.organization_id == organization.id,
                        Ticket.title == DEMO_TICKET_TITLE,
                    )
                )
            ).scalar_one_or_none()
            if ticket is None:
                ticket = Ticket(
                    organization_id=organization.id,
                    customer_id=customer.id,
                    created_by=user.id,
                    title=DEMO_TICKET_TITLE,
                    description=(
                        "A customer reports checkout failures after applying a coupon. "
                        "The payment service logs a retry exhaustion error. Investigate the "
                        "deployment, logs, and matching source code; do not assume a cause "
                        "without evidence."
                    ),
                    priority=TicketPriority.HIGH,
                    status=TicketStatus.OPEN,
                )
                db.add(ticket)
                await db.flush()
                db.add(
                    TicketEvent(
                        organization_id=organization.id,
                        ticket_id=ticket.id,
                        actor_user_id=user.id,
                        type=TicketEventType.CREATED,
                        payload={"title": ticket.title, "priority": ticket.priority.value},
                    )
                )

            for kind, config in config_by_kind.items():
                existing = (
                    await db.execute(
                        select(Integration).where(
                            Integration.organization_id == organization.id,
                            Integration.kind == kind,
                        )
                    )
                ).scalar_one_or_none()
                if existing is None:
                    db.add(
                        Integration(
                            organization_id=organization.id,
                            kind=kind,
                            provider=IntegrationProvider.LOCAL,
                            name=f"Shopmock {kind.value.lower().replace('_', ' ')}",
                            config=config,
                        )
                    )

            await db.commit()
            return f"Demo ready: {DEMO_EMAIL} / (DEMO_PASSWORD), ticket {ticket.id}"
    finally:
        await dispose_engine()


if __name__ == "__main__":
    print(asyncio.run(seed_demo()))
