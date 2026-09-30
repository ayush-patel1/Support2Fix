"""UUIDv7 generation.

We use v7 (not v4) for primary keys so they're time-ordered — see ADR-001
D2/D6 and system-design.md §6. Python's stdlib gains `uuid.uuid7()` in 3.14;
until the project's minimum supported version catches up (pyproject targets
3.11+), we generate it ourselves. This is the standard, minimal construction
from RFC 9562: a 48-bit millisecond timestamp, the version/variant bits, and
the rest random.
"""

import os
import time
import uuid


def uuid7() -> uuid.UUID:
    ts_ms = time.time_ns() // 1_000_000
    ts_bytes = ts_ms.to_bytes(6, "big")
    rand_bytes = bytearray(os.urandom(10))

    rand_bytes[0] = (rand_bytes[0] & 0x0F) | 0x70  # version 7
    rand_bytes[2] = (rand_bytes[2] & 0x3F) | 0x80  # variant RFC 9562

    return uuid.UUID(bytes=bytes(ts_bytes) + bytes(rand_bytes))
