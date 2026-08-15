"""
Cache access and participant-country matching.

This module is intentionally read-only.

The scraper/GitHub Action owns cache generation.
The backend only reads the published JSON cache.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DATA_CACHE = ROOT / "data" / "opportunities.json"
WEB_CACHE = ROOT / "web" / "opportunities.json"

CACHE_SCHEMA_VERSION = 1


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Cache file does not exist: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise ValueError(
            f"Cache root must be a JSON object: {path}"
        )

    return payload


def load_cache(
    published: bool = True,
) -> dict[str, Any]:
    """
    Load the published cache by default.

    The website/backend contract uses web/opportunities.json because
    that is the cache published alongside the frontend.

    `published=False` is useful for local/backend tests and explicitly
    selects the canonical data cache.
    """

    path = WEB_CACHE if published else DATA_CACHE

    payload = _load_json(path)

    opportunities = payload.get(
        "opportunities"
    )

    if not isinstance(opportunities, list):
        raise ValueError(
            "Cache does not contain an opportunities list."
        )

    return payload


def _normalize_country_code(
    country: Any,
) -> str:
    """
    Normalize a participant-country code.

    The cache is expected to contain ISO-3166 alpha-2 codes, but the
    matching function deliberately normalizes the input so callers can
    use `ma`, `MA`, or ` Ma ` interchangeably.
    """

    if not isinstance(country, str):
        return ""

    return country.strip().upper()


def opportunity_matches_country(
    opportunity: dict[str, Any],
    country: str,
) -> bool:
    """
    Return True when an opportunity is available to the requested
    participant country.

    Matching is case-insensitive and whitespace-safe.
    """

    requested = _normalize_country_code(country)

    if not requested:
        return False

    eligible = opportunity.get(
        "eligible_countries",
        [],
    )

    if not isinstance(eligible, list):
        return False

    normalized_eligible = {
        _normalize_country_code(value)
        for value in eligible
        if isinstance(value, str)
    }

    normalized_eligible.discard("")

    return requested in normalized_eligible


def search_country(
    country: str,
    *,
    published: bool = True,
) -> list[dict[str, Any]]:
    """
    Search cached opportunities for a participant country.

    The backend performs no live ESC request here. Live data is brought
    into the cache by the scheduled scraper workflow.
    """

    requested = _normalize_country_code(country)

    if len(requested) != 2:
        raise ValueError(
            "Participant country must be a two-letter ISO country code."
        )

    payload = load_cache(
        published=published
    )

    opportunities = payload.get(
        "opportunities",
        [],
    )

    return [
        opportunity
        for opportunity in opportunities
        if isinstance(opportunity, dict)
        and opportunity_matches_country(
            opportunity,
            requested,
        )
    ]
