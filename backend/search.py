"""
Command-line participant-country search.

Usage:
    python -m backend.search MA
"""

from __future__ import annotations

import json
import sys

from .cache import search_country


def build_response(country: str) -> dict:
    normalized = country.strip().upper()

    if len(normalized) != 2:
        raise ValueError(
            "Participant country must be a two-letter ISO country code."
        )

    opportunities = search_country(
        normalized
    )

    return {
        "status": "success",
        "participant_country": normalized,
        "count": len(opportunities),
        "opportunities": opportunities,
    }


def main() -> int:
    if len(sys.argv) != 2:
        payload = {
            "status": "error",
            "error": (
                "Usage: python -m backend.search "
                "<ISO country code>"
            ),
        }

        print(
            json.dumps(
                payload,
                ensure_ascii=False,
            )
        )

        return 2

    country = sys.argv[1]

    try:
        payload = build_response(
            country
        )
    except (
        FileNotFoundError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        payload = {
            "status": "error",
            "error": str(exc),
        }

        print(
            json.dumps(
                payload,
                ensure_ascii=False,
            )
        )

        return 1

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
