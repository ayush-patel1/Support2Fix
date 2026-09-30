"""Password hashing and session-token helpers.

See security.md §10. Passwords use argon2id (via argon2-cffi's high-level
PasswordHasher, which defaults to argon2id). Session tokens are random,
sent to the client as an opaque cookie value, and stored server-side only
as a SHA-256 hash — the raw token never touches the database, so a DB leak
alone can't be replayed as a valid session.
"""

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def generate_session_token() -> str:
    """256 bits of randomness, URL-safe — this is the raw cookie value."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """One-way hash stored in the `sessions` table. Lookups hash the

    incoming cookie value and query by this hash — never by the raw token.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
