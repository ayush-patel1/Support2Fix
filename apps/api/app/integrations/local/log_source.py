"""LogSource backed by a local JSON-Lines file — no log aggregator, no

network. This is the local adapter for the `LogSource` interface; a real
deployment would swap in something like a CloudWatch or Datadog adapter
satisfying the same `Protocol` (see app/integrations/base.py).

Each log line's 0-indexed position in the file is its `event_id` — stable
as long as the file isn't rewritten, which is fine for a static fixture
like shopmock's `logs/application.jsonl`.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from app.core.errors import NotFoundError
from app.integrations.types import LogEntry


class LocalFileLogSource:
    def __init__(self, log_path: str) -> None:
        self.log_path = Path(log_path).resolve()
        if not self.log_path.is_file():
            raise ValueError(f"{self.log_path} is not a file.")

    def _read_all(self) -> list[LogEntry]:
        entries = []
        with self.log_path.open(encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                raw = json.loads(line)
                entries.append(
                    LogEntry(
                        id=str(i),
                        timestamp=datetime.fromisoformat(raw["timestamp"]),
                        level=raw["level"],
                        service=raw["service"],
                        message=raw["message"],
                        raw=raw,
                    )
                )
        return entries

    async def search(
        self,
        query: str,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> list[LogEntry]:
        entries = await asyncio.to_thread(self._read_all)
        query_lower = query.lower()
        matched = []
        for entry in entries:
            if since is not None and entry.timestamp < since:
                continue
            if until is not None and entry.timestamp > until:
                continue
            if query_lower not in entry.message.lower():
                continue
            matched.append(entry)
            if len(matched) >= limit:
                break
        return matched

    async def get_event(self, event_id: str) -> LogEntry:
        try:
            index = int(event_id)
        except ValueError:
            raise ValueError(
                f"Invalid event id {event_id!r}: expected a line-index integer."
            ) from None

        entries = await asyncio.to_thread(self._read_all)
        if not (0 <= index < len(entries)):
            raise NotFoundError(f"No log event at index {index}.")
        return entries[index]
