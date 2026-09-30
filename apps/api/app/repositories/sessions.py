import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session


class SessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_token_hash(self, token_hash: str) -> Session | None:
        stmt = select(Session).where(Session.token_hash == token_hash)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        token_hash: str,
        active_organization_id: uuid.UUID | None,
        expires_at: datetime,
    ) -> Session:
        session = Session(
            user_id=user_id,
            token_hash=token_hash,
            active_organization_id=active_organization_id,
            expires_at=expires_at,
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def touch(self, session: Session) -> None:
        session.last_seen_at = datetime.now(UTC)
        await self.db.flush()

    async def set_active_organization(self, session: Session, organization_id: uuid.UUID) -> None:
        session.active_organization_id = organization_id
        await self.db.flush()

    async def delete(self, session: Session) -> None:
        await self.db.delete(session)
        await self.db.flush()

    async def delete_by_token_hash(self, token_hash: str) -> None:
        session = await self.get_by_token_hash(token_hash)
        if session is not None:
            await self.delete(session)
