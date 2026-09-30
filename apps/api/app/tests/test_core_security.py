"""Unit tests for core helpers that the auth flow depends on. No database."""

import time

from app.core.ids import uuid7
from app.core.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.core.slug import candidate_slugs, slugify


def test_uuid7_has_version_and_variant_bits():
    u = uuid7()
    assert u.version == 7
    assert u.variant == "specified in RFC 4122"


def test_uuid7_is_time_ordered():
    first = uuid7()
    time.sleep(0.002)  # cross a millisecond boundary
    second = uuid7()
    assert first < second


def test_password_hash_roundtrip_uses_argon2id():
    hashed = hash_password("correct-horse")
    assert hashed.startswith("$argon2id$")
    assert verify_password("correct-horse", hashed)
    assert not verify_password("wrong-horse", hashed)


def test_session_tokens_are_random_and_only_stored_hashed():
    a, b = generate_session_token(), generate_session_token()
    assert a != b
    assert len(a) >= 43  # 32 random bytes, base64url

    digest = hash_session_token(a)
    assert digest != a
    assert len(digest) == 64  # sha256 hex
    assert hash_session_token(a) == digest  # deterministic, so lookups work


def test_slugify_and_collision_candidates():
    assert slugify("  Acme, Inc.  ") == "acme-inc"
    assert slugify("!!!") == "org"

    candidates = candidate_slugs("Acme")
    assert candidates[:3] == ["acme", "acme-2", "acme-3"]
    assert candidates[-1].startswith("acme-") and len(candidates) == len(set(candidates))
