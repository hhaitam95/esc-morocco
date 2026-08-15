import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data"

CACHE_FILE = DATA_DIR / "opportunities.json"
INDEX_FILE = DATA_DIR / "participant_country_index.json"
MANIFEST_FILE = DATA_DIR / "cache_manifest.json"


class CacheError(RuntimeError):
    """Raised when the opportunity cache cannot be served safely."""


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

    if not isinstance(
        data,
        dict,
    ):
        raise CacheError(
            "Opportunity cache must be a JSON object."
        )

    opportunities = data.get(
        "opportunities",
        [],
    )

    if not isinstance(
        opportunities,
        list,
    ):
        raise CacheError(
            "Opportunity cache contains an invalid opportunities list."
        )

    return data


def load_participant_country_index():
    data = load_json(INDEX_FILE)

    if not isinstance(
        data,
        dict,
    ):
        raise CacheError(
            "Participant-country index must be a JSON object."
        )

    countries = data.get(
        "countries",
        {}
    )

    if not isinstance(
        countries,
        dict,
    ):
        raise CacheError(
            "Participant-country index contains an invalid countries object."
        )

    return data


def load_manifest():
    if not MANIFEST_FILE.exists():
        return None

    return load_json(
        MANIFEST_FILE
    )


def normalize_country_code(value):
    if value is None:
        return ""

    value = str(value).strip().upper()

    if len(value) != 2:
        return ""

    if not value.isalpha():
        return ""

    return value


def opportunity_matches_country(
    opportunity,
    country_code,
):
    """
    Return True when an opportunity is eligible for
    the requested participant country.

    This helper remains available for validation and
    backward compatibility. Production search uses
    the participant-country index.
    """

    if not isinstance(
        opportunity,
        dict,
    ):
        return False

    requested = normalize_country_code(
        country_code
    )

    if not requested:
        return False

    eligible = opportunity.get(
        "eligible_countries",
        [],
    )

    if not isinstance(
        eligible,
        list,
    ):
        return False

    return requested in {
        str(value).strip().upper()
        for value in eligible
        if isinstance(
            value,
            str,
        )
    }


def search_cache(country_code):
    country_code = normalize_country_code(
        country_code
    )

    if not country_code:
        raise ValueError(
            "A valid two-letter participant country code is required."
        )

    data = load_cache()
    index = load_participant_country_index()

    opportunities = data.get(
        "opportunities",
        [],
    )

    opportunities_by_id = {}

    for opportunity in opportunities:
        if not isinstance(
            opportunity,
            dict,
        ):
            continue

        opportunity_id = opportunity.get(
            "id"
        )

        if opportunity_id is None:
            continue

        opportunities_by_id[
            str(opportunity_id)
        ] = opportunity

    indexed_ids = index.get(
        "countries",
        {}
    ).get(
        country_code,
        []
    )

    if not isinstance(
        indexed_ids,
        list,
    ):
        raise CacheError(
            f"Invalid index entry for participant country {country_code}."
        )

    matches = []

    seen = set()

    for opportunity_id in indexed_ids:
        identity = str(
            opportunity_id
        )

        if identity in seen:
            continue

        opportunity = opportunities_by_id.get(
            identity
        )

        if opportunity is None:
            raise CacheError(
                "Participant-country index references "
                f"missing opportunity {opportunity_id}."
            )

        if not opportunity_matches_country(
            opportunity,
            country_code,
        ):
            raise CacheError(
                "Participant-country index contains an "
                f"incorrect mapping for opportunity {opportunity_id}."
            )

        matches.append(
            opportunity
        )

        seen.add(identity)

    return {
        "status": "success",
        "participant_country": country_code,
        "count": len(matches),
        "opportunities": matches,
        "cache": {
            "generated_at": data.get(
                "generated_at"
            ),
            "schema_version": data.get(
                "schema_version"
            ),
            "cache_schema_version": data.get(
                "cache_schema_version"
            ),
            "participant_country_index_schema_version": index.get(
                "schema_version"
            ),
            "participant_country_index_generated_at": index.get(
                "generated_at"
            ),
        },
    }
