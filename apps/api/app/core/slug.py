"""Slugify an organization name into a URL-safe, unique identifier."""

import re
import secrets

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    slug = _NON_ALNUM.sub("-", text.lower()).strip("-")
    return slug or "org"


def candidate_slugs(name: str) -> "list[str]":
    """Yields a base slug, then a few `base-2`, `base-3`, ... variants, then

    a random-suffixed fallback. The caller (OrganizationRepository) tries
    these in order against the unique constraint until one doesn't collide.
    """
    base = slugify(name)
    candidates = [base, *(f"{base}-{n}" for n in range(2, 6))]
    candidates.append(f"{base}-{secrets.token_hex(4)}")
    return candidates
