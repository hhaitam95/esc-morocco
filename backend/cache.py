import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data"

CACHE_FILE = DATA_DIR / "opportunities.json"
MANIFEST_FILE = DATA_DIR / "cache_manifest.json"


class CacheError(RuntimeError):
    pass


def load_json(path):
    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise CacheError(
            f"Cache file does not exist: {path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise CacheError(
            f"Invalid JSON in cache file: {path}"
        ) from exc


def load_cache():
    data = load_json(CACHE_FILE)

    if not isinstance(data, dict):
        raise CacheError(
            "Opportunity cache must be a JSON object."
        )

    opportunities = data.get(
        "opportunities",
        [],
    )

    if not isinstance(opportunities, list):
        raise CacheError(
            "Opportunity cache contains an invalid opportunities list."
        )

    return data


def load_manifest():
    if not MANIFEST_FILE.exists():
        return None

    return load_json(MANIFEST_FILE)


def normalize_country_code(value):
    if value is None:
        return ""

    value = str(value).strip().upper()

    if len(value) != 2:
        return ""

    return value


def opportunity_matches_country(
    opportunity,
    country_code,
):
    eligible = opportunity.get(
        "eligible_countries",
        [],
    )

    if not isinstance(eligible, list):
        return False

    normalized = {
        normalize_country_code(value)
        for value in eligible
    }

    normalized.discard("")

    return country_code in normalized


def search_cache(country_code):
    country_code = normalize_country_code(
        country_code
    )

    if not country_code:
        raise ValueError(
            "A valid two-letter participant country code is required."
        )

    data = load_cache()

    opportunities = data.get(
        "opportunities",
        [],
    )

    matches = [
        opportunity
        for opportunity in opportunities
        if isinstance(opportunity, dict)
        and opportunity_matches_country(
            opportunity,
            country_code,
        )
    ]

    return {
        "status": "success",
        "participant_country": country_code,
        "count": len(matches),
        "opportunities": matches,
        "cache": {
            "generated_at": data.get("generated_at"),
            "schema_version": data.get("schema_version"),
        },
    }
