"""SQLAlchemy ORM models. Import every model module here so Alembic's

autogenerate (env.py imports `app.models`) sees the full metadata.
"""

from app.models.customer import (
    CodeRepository,
    Customer,
    CustomerEnvironment,
    CustomerTier,
    Deployment,
    DeploymentStatus,
    RepositoryProvider,
    Service,
)
from app.models.integration import Integration, IntegrationKind, IntegrationProvider
from app.models.investigation import (
    Investigation,
    InvestigationEvent,
    InvestigationEventType,
    InvestigationJob,
    InvestigationStatus,
)
from app.models.membership import Membership, Role
from app.models.organization import Organization
from app.models.session import Session
from app.models.ticket import Ticket, TicketEvent, TicketEventType, TicketPriority, TicketStatus
from app.models.tool_call import Evidence, ToolCall
from app.models.user import User

__all__ = [
    "CodeRepository",
    "Customer",
    "CustomerEnvironment",
    "CustomerTier",
    "Deployment",
    "DeploymentStatus",
    "Evidence",
    "Integration",
    "IntegrationKind",
    "IntegrationProvider",
    "Investigation",
    "InvestigationEvent",
    "InvestigationEventType",
    "InvestigationJob",
    "InvestigationStatus",
    "Membership",
    "Organization",
    "RepositoryProvider",
    "Role",
    "Service",
    "Session",
    "Ticket",
    "TicketEvent",
    "TicketEventType",
    "TicketPriority",
    "TicketStatus",
    "ToolCall",
    "User",
]
