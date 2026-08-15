#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent

CANONICAL_CACHE = ROOT / "data" / "opportunities.json"
PUBLISHED_CACHE = ROOT / "web" / "opportunities.json"

PARTICIPANT_INDEX = ROOT / "data" / "participant_country_index.json"
PUBLISHED_PARTICIPANT_INDEX = ROOT / "web" / "participant_country_index.json"

MANIFEST = ROOT / "data" / "cache_manifest.json"

BACKEND_CACHE = ROOT / "backend" / "cache.py"
BACKEND_SEARCH = ROOT / "backend" / "search.py"
BACKEND_TESTS = ROOT / "backend" / "test_search.py"

SCRAPER = ROOT / "scraper" / "scraper.py"

REQUIRED_FILES = [
    "backend/__init__.py",
    "backend/cache.py",
    "backend/search.py",
    "backend/test_search.py",
    "data/opportunities.json",
    "scraper/scraper.py",
    "web/app.js",
    "web/opportunities.json",
]

PHASE_FOUR_FILES = [
    "backend/cache.py",
    "backend/search.py",
    "backend/test_search.py",
    "data/cache_manifest.json",
    "data/participant_country_index.json",
    "web/participant_country_index.json",
    "update.py",
]

INDEX_SCHEMA_VERSION = 1

COUNTRY_NAME_ALIASES = {
    "el": "GR",
    "greece": "GR",
    "uk": "GB",
    "united kingdom": "GB",
    "turkey": "TR",
    "türkiye": "TR",
    "czech republic": "CZ",
    "czechia": "CZ",
    "north macedonia": "MK",
    "the former yugoslav republic of macedonia": "MK",
    "macedonia": "MK",
    "republic of moldova": "MD",
    "moldova": "MD",
    "kosovo": "XK",
    "kosovo * un resolution": "XK",
    "bonaire, sint eustatius and saba": "BQ",
    "bonaire sint eustatius and saba": "BQ",
    "caribbean netherlands": "BQ",
    "curacao": "CW",
    "curaçao": "CW",
    "sint maarten": "SX",
    "sint maarten (dutch part)": "SX",
    "palestine": "PS",
    "palestine, state of": "PS",
    "russia": "RU",
    "russian federation": "RU",
    "syria": "SY",
    "syrian arab republic": "SY",
}

COUNTRY_DISPLAY_OVERRIDES = {
    "TR": "Türkiye",
    "CZ": "Czechia",
    "MK": "North Macedonia",
    "BA": "Bosnia and Herzegovina",
    "CW": "Curaçao",
    "SX": "Sint Maarten",
    "BQ": "Bonaire, Sint Eustatius and Saba",
    "XK": "Kosovo",
}


def run(command, *, check=True, capture=False):
    print("$ " + " ".join(str(item) for item in command))

    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=capture,
    )

    if capture:
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)

    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}: "
            + " ".join(str(item) for item in command)
        )

    return result


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path):
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc


def atomic_write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_suffix(path.suffix + ".tmp")

    temporary.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
            sort_keys=False,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary.replace(path)


def normalize_country_text(value):
    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value).strip(),
    ).casefold()


def country_code_from_value(value):
    """
    Resolve a participant-country value to an ISO-style two-letter code.

    The scraper already performs this normalization, but Phase Four also
    normalizes the existing cache so the index can safely be generated from
    older cache records containing country names.
    """

    if value is None:
        return None

    raw = re.sub(
        r"\s+",
        " ",
        str(value).strip(),
    )

    if not raw:
        return None

    normalized = normalize_country_text(raw)

    if normalized in COUNTRY_NAME_ALIASES:
        return COUNTRY_NAME_ALIASES[normalized]

    if len(raw) == 2 and raw.isalpha():
        code = raw.upper()

        if code == "EL":
            return "GR"

        if code == "UK":
            return "GB"

        if code == "XK":
            return "XK"

        try:
            import pycountry

            record = pycountry.countries.get(alpha_2=code)

            if record:
                return code
        except (ImportError, LookupError):
            pass

    cleaned = re.sub(
        r"\s*\*.*$",
        "",
        raw,
    ).strip()

    cleaned_normalized = normalize_country_text(cleaned)

    if cleaned_normalized in COUNTRY_NAME_ALIASES:
        return COUNTRY_NAME_ALIASES[cleaned_normalized]

    try:
        import pycountry

        for field in (
            "name",
            "official_name",
            "common_name",
        ):
            try:
                record = pycountry.countries.get(**{field: cleaned})

                if record:
                    return record.alpha_2.upper()
            except LookupError:
                continue

        try:
            matches = pycountry.countries.search_fuzzy(cleaned)

            if matches:
                return matches[0].alpha_2.upper()
        except LookupError:
            pass

    except ImportError:
        pass

    return None


def country_display_name(code):
    normalized = str(code).strip().upper()

    if normalized in COUNTRY_DISPLAY_OVERRIDES:
        return COUNTRY_DISPLAY_OVERRIDES[normalized]

    try:
        import pycountry

        record = pycountry.countries.get(alpha_2=normalized)

        if record:
            return (
                getattr(
                    record,
                    "common_name",
                    None,
                )
                or record.name
            )
    except (ImportError, LookupError):
        pass

    return normalized


def require_files():
    print("Checking required files...")

    missing = [
        relative for relative in REQUIRED_FILES if not (ROOT / relative).is_file()
    ]

    if missing:
        raise RuntimeError(
            "Missing required files:\n" + "\n".join(f"  - {item}" for item in missing)
        )

    print("PASS: required files exist.")


def check_git_state():
    print("\nChecking Git state...")

    result = run(
        ["git", "status", "--short"],
        capture=True,
    )

    status = result.stdout

    if status.strip():
        print("Current working tree:")
        print(
            status,
            end="" if status.endswith("\n") else "\n",
        )
        print("NOTE: Existing working-tree changes were detected.")
        print(
            "NOTE: This updater will stage only explicitly "
            "declared Phase Four files."
        )
        print("NOTE: Unrelated changes will not be included.")
    else:
        print("PASS: working tree is clean before this update.")


def check_branch():
    print("\nChecking branch...")

    result = run(
        ["git", "branch", "--show-current"],
        capture=True,
    )

    branch = result.stdout.strip()

    if branch != "main":
        raise RuntimeError(f"Expected branch 'main', found '{branch}'.")

    print("PASS: current branch is main.")


def check_remote():
    print("\nChecking remote safety...")

    run(["git", "fetch", "origin", "main"])

    result = run(
        [
            "git",
            "rev-list",
            "--left-right",
            "--count",
            "main...origin/main",
        ],
        capture=True,
    )

    values = result.stdout.strip().split()

    if len(values) != 2:
        raise RuntimeError("Unable to determine local/remote synchronization state.")

    local_only, remote_only = map(int, values)

    print(f"Local-only commits: {local_only}")
    print(f"Remote-only commits: {remote_only}")

    if remote_only != 0:
        raise RuntimeError(
            "Remote main contains commits not present locally. "
            "Refusing to modify/commit/push."
        )

    if local_only != 0:
        raise RuntimeError(
            "Local main contains commits not present remotely. "
            "Refusing to modify/commit/push."
        )

    print("PASS: local main is synchronized with origin/main.")


def validate_scraper():
    print("\nValidating existing scraper architecture...")

    scraper = read_text(SCRAPER)

    required_markers = [
        "normalize_result_country_schema",
        "eligible_countries",
        "eligible_countries_unmapped",
        "eligibility_known",
        "CHECKPOINT_FILE",
        "OPPORTUNITIES_FILE",
        "BATCH_SIZE",
        "DETAIL_REQUEST_DELAY",
        "MAX_RETRIES",
    ]

    missing = [marker for marker in required_markers if marker not in scraper]

    if missing:
        raise RuntimeError(
            "Scraper architecture validation failed. "
            "Missing markers:\n" + "\n".join(f"  - {item}" for item in missing)
        )

    print(
        "PASS: existing resumable/incremental " "scraper architecture remains intact."
    )


def validate_hourly_workflow():
    print("\nValidating hourly scraper workflow...")

    workflow_candidates = [
        ROOT / ".github" / "workflows" / "update.yml",
        ROOT / ".github" / "workflows" / "scrape.yml",
    ]

    workflow = next(
        (path for path in workflow_candidates if path.is_file()),
        None,
    )

    if workflow is None:
        raise RuntimeError("No background scraper workflow was found.")

    content = read_text(workflow)

    if "schedule:" not in content:
        raise RuntimeError("Background scraper workflow does not contain a schedule.")

    if "cron:" not in content:
        raise RuntimeError(
            "Background scraper workflow does not contain a cron schedule."
        )

    print(
        f"PASS: hourly scraper workflow is present " f"({workflow.relative_to(ROOT)})."
    )


def load_canonical_cache():
    print("\nValidating canonical opportunity cache...")

    data = load_json(CANONICAL_CACHE)

    if not isinstance(data, dict):
        raise RuntimeError("Canonical cache must be a JSON object.")

    opportunities = data.get("opportunities")

    if not isinstance(opportunities, list):
        raise RuntimeError("Canonical cache does not contain an opportunities list.")

    if not opportunities:
        raise RuntimeError("Canonical cache is empty.")

    seen_ids = set()
    duplicate_ids = []

    with_country_data = 0
    unknown_country_data = 0

    for opportunity in opportunities:
        if not isinstance(opportunity, dict):
            raise RuntimeError("Canonical cache contains a non-object opportunity.")

        opportunity_id = opportunity.get("id")

        if opportunity_id is None:
            raise RuntimeError("Canonical cache contains an opportunity without an ID.")

        identity = str(opportunity_id)

        if identity in seen_ids:
            duplicate_ids.append(identity)

        seen_ids.add(identity)

        countries = opportunity.get("eligible_countries")

        if isinstance(countries, list):
            with_country_data += 1

        if opportunity.get("eligibility_known") is False:
            unknown_country_data += 1

    if duplicate_ids:
        raise RuntimeError(
            "Canonical cache contains duplicate opportunity IDs:\n"
            + "\n".join(f"  - {item}" for item in sorted(set(duplicate_ids)))
        )

    print(f"Cached opportunities: {len(opportunities)}")
    print("Opportunities with participant-country data: " f"{with_country_data}")

    if unknown_country_data:
        print(
            "NOTE: opportunities with unknown participant-country "
            f"eligibility: {unknown_country_data}"
        )

    print("PASS: canonical cache is structurally valid.")

    return data


def load_published_cache():
    print("\nValidating published website cache...")

    data = load_json(PUBLISHED_CACHE)

    if not isinstance(data, dict):
        raise RuntimeError("Published cache must be a JSON object.")

    opportunities = data.get("opportunities")

    if not isinstance(opportunities, list):
        raise RuntimeError("Published cache does not contain an opportunities list.")

    if not opportunities:
        raise RuntimeError("Published cache is empty.")

    print(f"Web cached opportunities: {len(opportunities)}")
    print("PASS: published website cache is structurally valid.")

    return data


def validate_canonical_published_ids(
    canonical_data,
    published_data,
):
    print("\nValidating canonical/published opportunity consistency...")

    canonical_ids = {
        str(item.get("id"))
        for item in canonical_data.get(
            "opportunities",
            [],
        )
        if isinstance(item, dict) and item.get("id") is not None
    }

    published_ids = {
        str(item.get("id"))
        for item in published_data.get(
            "opportunities",
            [],
        )
        if isinstance(item, dict) and item.get("id") is not None
    }

    if canonical_ids != published_ids:
        missing_from_web = sorted(canonical_ids - published_ids)
        missing_from_canonical = sorted(published_ids - canonical_ids)

        raise RuntimeError(
            "Canonical and published caches contain different "
            "opportunity IDs.\n"
            f"Missing from web cache: {missing_from_web}\n"
            f"Missing from canonical cache: {missing_from_canonical}"
        )

    print("PASS: canonical and published caches contain " "the same opportunity IDs.")


def normalize_opportunity_country_values(
    canonical_data,
):
    """
    Normalize participant-country values in the canonical cache.

    The scraper's current schema already stores ISO-style codes.
    This function also supports older cache records containing names,
    allowing Phase Four to safely migrate the existing dataset.
    """

    opportunities = canonical_data.get(
        "opportunities",
        [],
    )

    normalized_count = 0
    unmapped_values = set()

    for opportunity in opportunities:
        if not isinstance(opportunity, dict):
            continue

        values = opportunity.get(
            "eligible_countries",
            [],
        )

        if not isinstance(values, list):
            continue

        codes = set()
        original_unmapped = set(
            opportunity.get(
                "eligible_countries_unmapped",
                [],
            )
            or []
        )

        for value in values:
            code = country_code_from_value(value)

            if code:
                codes.add(code.upper())
            else:
                text = str(value).strip()

                if text:
                    unmapped_values.add(text)
                    original_unmapped.add(text)

        normalized_codes = sorted(codes)

        if normalized_codes != values:
            opportunity["eligible_countries"] = normalized_codes
            normalized_count += 1

        if original_unmapped:
            opportunity["eligible_countries_unmapped"] = sorted(original_unmapped)
        else:
            opportunity.pop(
                "eligible_countries_unmapped",
                None,
            )

        opportunity["eligibility_known"] = bool(normalized_codes or values == [])

    if normalized_count:
        print(
            "Normalized participant-country schema "
            f"for {normalized_count} cached opportunities."
        )
    else:
        print(
            "Participant-country values already use "
            "the canonical normalized representation."
        )

    if unmapped_values:
        print("WARNING: unmapped participant-country values:")

        for value in sorted(unmapped_values):
            print(f"  - {value}")

    return canonical_data, unmapped_values


def build_participant_country_index(
    canonical_data,
):
    print("\nBuilding participant-country index...")

    opportunities = canonical_data.get(
        "opportunities",
        [],
    )

    countries = {}

    indexed_opportunities = set()
    skipped_without_country_data = []

    for opportunity in opportunities:
        if not isinstance(opportunity, dict):
            continue

        opportunity_id = opportunity.get("id")

        if opportunity_id is None:
            continue

        countries_for_opportunity = opportunity.get(
            "eligible_countries",
            [],
        )

        if not isinstance(
            countries_for_opportunity,
            list,
        ):
            skipped_without_country_data.append(str(opportunity_id))
            continue

        normalized_codes = set()

        for value in countries_for_opportunity:
            code = country_code_from_value(value)

            if code:
                normalized_codes.add(code.upper())

        for code in normalized_codes:
            countries.setdefault(
                code,
                [],
            ).append(opportunity_id)

            indexed_opportunities.add(str(opportunity_id))

    for code in countries:
        countries[code] = sorted(
            countries[code],
            key=lambda value: (
                str(type(value)),
                str(value),
            ),
        )

    sorted_countries = dict(
        sorted(
            countries.items(),
            key=lambda item: item[0],
        )
    )

    generated_at = datetime.now(timezone.utc).isoformat()

    index = {
        "schema_version": INDEX_SCHEMA_VERSION,
        "generated_at": generated_at,
        "opportunity_count": len(opportunities),
        "participant_country_count": len(sorted_countries),
        "indexed_opportunity_count": len(indexed_opportunities),
        "countries": sorted_countries,
    }

    print(f"  Opportunities: {len(opportunities)}")
    print("  Participant countries indexed: " f"{len(sorted_countries)}")
    print("  Opportunities indexed: " f"{len(indexed_opportunities)}")

    if skipped_without_country_data:
        print(
            "  Opportunities skipped because participant-country "
            "data was unavailable: "
            f"{len(skipped_without_country_data)}"
        )

    if "MA" in sorted_countries:
        print("  Morocco (MA): " f"{len(sorted_countries['MA'])} opportunities")
    else:
        print("  Morocco (MA): 0 opportunities")

    return index


def validate_index(
    index,
    canonical_data,
):
    print("\nValidating participant-country index...")

    if not isinstance(
        index,
        dict,
    ):
        raise RuntimeError("Participant-country index must be a JSON object.")

    if index.get("schema_version") != INDEX_SCHEMA_VERSION:
        raise RuntimeError("Unexpected participant-country index schema version.")

    countries = index.get("countries")

    if not isinstance(
        countries,
        dict,
    ):
        raise RuntimeError(
            "Participant-country index does not contain a countries object."
        )

    canonical_by_id = {
        str(item.get("id")): item
        for item in canonical_data.get(
            "opportunities",
            [],
        )
        if isinstance(item, dict) and item.get("id") is not None
    }

    indexed_ids = set()

    for country_code, opportunity_ids in countries.items():
        if not isinstance(
            country_code,
            str,
        ):
            raise RuntimeError(
                "Participant-country index contains a non-string country key."
            )

        if (
            len(country_code) != 2
            or not country_code.isalpha()
            or country_code != country_code.upper()
        ):
            raise RuntimeError(
                f"Invalid participant-country index key: {country_code!r}"
            )

        if not isinstance(
            opportunity_ids,
            list,
        ):
            raise RuntimeError(f"Index entry for {country_code} is not a list.")

        previous = None

        for opportunity_id in opportunity_ids:
            identity = str(opportunity_id)

            if identity not in canonical_by_id:
                raise RuntimeError(
                    f"Index references unknown opportunity "
                    f"{opportunity_id} for {country_code}."
                )

            if previous is not None:
                current_sort = (
                    str(type(opportunity_id)),
                    str(opportunity_id),
                )

                if current_sort < previous:
                    raise RuntimeError(
                        f"Index entry for {country_code} is not deterministic."
                    )

                previous = current_sort
            else:
                previous = (
                    str(type(opportunity_id)),
                    str(opportunity_id),
                )

            indexed_ids.add(identity)

            opportunity = canonical_by_id[identity]

            eligible = {
                code
                for code in (
                    opportunity.get(
                        "eligible_countries",
                        [],
                    )
                    or []
                )
                if isinstance(
                    code,
                    str,
                )
            }

            if country_code not in {value.upper() for value in eligible}:
                raise RuntimeError(
                    f"Index incorrectly maps opportunity "
                    f"{opportunity_id} to {country_code}."
                )

    expected_pairs = set()

    for identity, opportunity in canonical_by_id.items():
        for value in (
            opportunity.get(
                "eligible_countries",
                [],
            )
            or []
        ):
            code = country_code_from_value(value)

            if code:
                expected_pairs.add(
                    (
                        code.upper(),
                        identity,
                    )
                )

    actual_pairs = {
        (
            country_code,
            str(opportunity_id),
        )
        for country_code, opportunity_ids in countries.items()
        for opportunity_id in opportunity_ids
    }

    if expected_pairs != actual_pairs:
        missing_pairs = sorted(expected_pairs - actual_pairs)
        unexpected_pairs = sorted(actual_pairs - expected_pairs)

        raise RuntimeError(
            "Participant-country index does not exactly match "
            "canonical eligibility data.\n"
            f"Missing index mappings: {missing_pairs[:20]}\n"
            f"Unexpected index mappings: {unexpected_pairs[:20]}"
        )

    print(
        "PASS: participant-country index exactly matches " "canonical eligibility data."
    )


def validate_morocco_index(index):
    print("\nValidating Morocco index entry...")

    countries = index.get("countries", {})

    morocco_ids = countries.get("MA", [])

    if not isinstance(
        morocco_ids,
        list,
    ):
        raise RuntimeError("Morocco index entry is not a list.")

    print(f"Morocco (MA) indexed opportunities: " f"{len(morocco_ids)}")

    if not morocco_ids:
        raise RuntimeError("Morocco (MA) has no indexed opportunities.")

    print(
        "PASS: Morocco is represented through the " "generic participant-country index."
    )


def update_manifest(
    canonical_data,
    index,
):
    print("\nUpdating cache manifest...")

    existing = {}

    if MANIFEST.exists():
        try:
            existing = load_json(MANIFEST)

            if not isinstance(
                existing,
                dict,
            ):
                existing = {}
        except RuntimeError:
            existing = {}

    manifest = dict(existing)

    manifest["cache_schema_version"] = canonical_data.get(
        "cache_schema_version",
        canonical_data.get(
            "schema_version",
            1,
        ),
    )

    manifest["opportunities"] = len(
        canonical_data.get(
            "opportunities",
            [],
        )
    )

    manifest["participant_countries"] = index.get(
        "participant_country_count",
        0,
    )

    manifest["participant_country_index_schema_version"] = INDEX_SCHEMA_VERSION

    manifest["participant_country_index_file"] = "participant_country_index.json"

    manifest["participant_country_index_generated_at"] = index.get("generated_at")

    atomic_write_json(
        MANIFEST,
        manifest,
    )

    print(f"  Opportunities: {manifest['opportunities']}")
    print("  Participant countries: " f"{manifest['participant_countries']}")
    print("PASS: cache manifest updated.")


def update_backend_cache():
    print("\nUpdating backend cache layer...")

    content = '''import json
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
'''

    BACKEND_CACHE.write_text(
        content,
        encoding="utf-8",
    )

    print("PASS: backend cache layer now uses " "the participant-country index.")


def update_backend_search():
    print("\nValidating backend search entry point...")

    content = """import json
import sys

from .cache import search_cache


def main():
    if len(sys.argv) != 2:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": (
                        "Usage: python -m backend.search "
                        "<participant-country-code>"
                    ),
                    "example": (
                        "python -m backend.search MA"
                    ),
                },
                ensure_ascii=False,
            )
        )

        return 1

    country_code = sys.argv[1]

    try:
        payload = search_cache(
            country_code
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": str(exc),
                },
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
"""

    BACKEND_SEARCH.write_text(
        content,
        encoding="utf-8",
    )

    print("PASS: backend search entry point remains " "country-agnostic.")


def update_backend_tests():
    print("\nUpdating backend index tests...")

    content = """import unittest

from .cache import (
    load_cache,
    load_participant_country_index,
    opportunity_matches_country,
    search_cache,
)


class CacheTests(unittest.TestCase):

    def test_cache_loads(self):
        data = load_cache()

        self.assertIsInstance(
            data,
            dict,
        )

        self.assertIsInstance(
            data.get("opportunities"),
            list,
        )

    def test_participant_country_index_loads(self):
        index = load_participant_country_index()

        self.assertIsInstance(
            index,
            dict,
        )

        self.assertIsInstance(
            index.get("countries"),
            dict,
        )

    def test_opportunity_country_matching(self):
        opportunity = {
            "id": "TEST-1",
            "eligible_countries": [
                "MA",
                "FR",
            ],
        }

        self.assertTrue(
            opportunity_matches_country(
                opportunity,
                "MA",
            )
        )

        self.assertTrue(
            opportunity_matches_country(
                opportunity,
                "FR",
            )
        )

        self.assertFalse(
            opportunity_matches_country(
                opportunity,
                "DE",
            )
        )

    def test_country_code_is_case_insensitive(self):
        opportunity = {
            "id": "TEST-2",
            "eligible_countries": [
                "MA",
            ],
        }

        self.assertTrue(
            opportunity_matches_country(
                opportunity,
                "ma",
            )
        )

    def test_invalid_country_is_rejected(self):
        with self.assertRaises(
            ValueError
        ):
            search_cache(
                "MOR"
            )

    def test_search_returns_expected_shape(self):
        payload = search_cache(
            "MA"
        )

        self.assertEqual(
            payload["status"],
            "success",
        )

        self.assertEqual(
            payload["participant_country"],
            "MA",
        )

        self.assertIsInstance(
            payload["count"],
            int,
        )

        self.assertIsInstance(
            payload["opportunities"],
            list,
        )

    def test_index_search_matches_direct_scan(self):
        data = load_cache()

        direct_matches = [
            opportunity
            for opportunity in data.get(
                "opportunities",
                [],
            )
            if opportunity_matches_country(
                opportunity,
                "MA",
            )
        ]

        indexed_result = search_cache(
            "MA"
        )

        self.assertEqual(
            len(direct_matches),
            indexed_result["count"],
        )

        direct_ids = {
            str(item["id"])
            for item in direct_matches
        }

        indexed_ids = {
            str(item["id"])
            for item in indexed_result["opportunities"]
        }

        self.assertEqual(
            direct_ids,
            indexed_ids,
        )

    def test_index_search_is_country_agnostic(self):
        index = load_participant_country_index()

        countries = index.get(
            "countries",
            {},
        )

        self.assertIn(
            "MA",
            countries,
        )

        self.assertGreater(
            len(countries),
            1,
        )

        for country_code in list(countries)[:3]:
            payload = search_cache(
                country_code
            )

            self.assertEqual(
                payload["status"],
                "success",
            )

            self.assertEqual(
                payload["participant_country"],
                country_code,
            )


if __name__ == "__main__":
    unittest.main()
"""

    BACKEND_TESTS.write_text(
        content,
        encoding="utf-8",
    )

    print("PASS: backend participant-country index tests updated.")


def publish_index(index):
    print("\nPublishing participant-country index...")

    atomic_write_json(
        PARTICIPANT_INDEX,
        index,
    )

    atomic_write_json(
        PUBLISHED_PARTICIPANT_INDEX,
        index,
    )

    print("PASS: participant-country index published " "to data/ and web/.")


def validate_published_index():
    print("\nValidating published participant-country index...")

    data_index = load_json(PARTICIPANT_INDEX)

    web_index = load_json(PUBLISHED_PARTICIPANT_INDEX)

    if data_index != web_index:
        raise RuntimeError("Data and web participant-country indexes differ.")

    print("PASS: data and web participant-country indexes are identical.")


def validate_index_against_published_cache():
    print("\nValidating index against published opportunity cache...")

    index = load_json(PUBLISHED_PARTICIPANT_INDEX)

    published = load_json(PUBLISHED_CACHE)

    validate_index(
        index,
        published,
    )

    print(
        "PASS: published participant-country index "
        "matches published opportunity cache."
    )


def validate_python():
    print("\nRunning Python syntax validation...")

    python_files = [
        "backend/__init__.py",
        "backend/cache.py",
        "backend/search.py",
        "backend/test_search.py",
        "scraper/scraper.py",
        "update.py",
    ]

    run(
        [
            sys.executable,
            "-m",
            "py_compile",
            *[str(ROOT / path) for path in python_files],
        ]
    )

    print("PASS: Python syntax validation passed.")


def run_backend_tests():
    print("\nRunning backend tests...")

    run(
        [
            sys.executable,
            "-m",
            "unittest",
            "backend.test_search",
            "-v",
        ]
    )

    print("PASS: backend participant-country index tests passed.")


def validate_country_search():
    print("\nValidating Morocco cache-first indexed search...")

    result = run(
        [
            sys.executable,
            "-m",
            "backend.search",
            "MA",
        ],
        capture=True,
    )

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Morocco indexed search did not return valid JSON.") from exc

    if payload.get("status") != "success":
        raise RuntimeError(f"Morocco indexed search failed: {payload!r}")

    if payload.get("participant_country") != "MA":
        raise RuntimeError(
            "Morocco indexed search returned the wrong participant country."
        )

    count = payload.get("count")

    if not isinstance(
        count,
        int,
    ):
        raise RuntimeError("Morocco indexed search count is not an integer.")

    if count <= 0:
        raise RuntimeError("Morocco indexed search returned zero opportunities.")

    print(f"  Morocco (MA) results: {count}")

    print("PASS: Morocco indexed cache-first search works.")


def validate_country_independence():
    print("\nValidating country-agnostic index design...")

    index = load_json(PARTICIPANT_INDEX)

    countries = index.get("countries", {})

    if "MA" not in countries:
        raise RuntimeError(
            "Morocco (MA) is missing from the participant-country index."
        )

    if len(countries) < 2:
        raise RuntimeError(
            "Participant-country index contains only one country. "
            "The index must remain country-agnostic."
        )

    print(f"Indexed participant countries: {len(countries)}")

    print("PASS: participant-country index is country-agnostic.")


def validate_frontend_compatibility():
    print("\nValidating frontend cache compatibility...")

    app = read_text(ROOT / "web" / "app.js")

    if "opportunities.json" not in app:
        raise RuntimeError(
            "Frontend no longer references the published opportunity cache."
        )

    published = load_json(PUBLISHED_CACHE)

    opportunities = published.get("opportunities", [])

    for opportunity in opportunities:
        if not isinstance(
            opportunity,
            dict,
        ):
            raise RuntimeError("Published cache contains a non-object opportunity.")

        if not isinstance(
            opportunity.get("eligible_countries"),
            list,
        ):
            raise RuntimeError(
                "Published cache contains an opportunity without " "eligible_countries."
            )

    print(
        "PASS: existing frontend remains compatible with "
        "the canonical opportunity cache."
    )


def whitespace_check():
    print("\nRunning Git whitespace check...")

    run(
        [
            "git",
            "diff",
            "--check",
        ]
    )

    print("PASS: Git whitespace check passed.")


def selective_commit_and_push():
    print("\nPreparing selective Phase Four commit...")

    run(["git", "reset"])

    for relative in PHASE_FOUR_FILES:
        path = ROOT / relative

        if path.exists():
            run(
                [
                    "git",
                    "add",
                    "--",
                    relative,
                ]
            )

    staged = run(
        [
            "git",
            "diff",
            "--cached",
            "--name-only",
        ],
        capture=True,
    ).stdout.splitlines()

    unexpected = sorted(set(staged) - set(PHASE_FOUR_FILES))

    if unexpected:
        raise RuntimeError(
            "Unexpected files are staged:\n"
            + "\n".join(f"  - {item}" for item in unexpected)
        )

    if not staged:
        raise RuntimeError("No Phase Four changes are staged.")

    print("Files staged for Phase Four:")

    for path in staged:
        print(f"  {path}")

    print("\nReviewing staged diff statistics...")

    run(
        [
            "git",
            "diff",
            "--cached",
            "--stat",
        ]
    )

    print("\nCreating Phase Four commit...")

    run(
        [
            "git",
            "commit",
            "-m",
            "feat: add participant-country index",
        ]
    )

    print("\nPushing Phase Four commit...")

    run(
        [
            "git",
            "push",
            "origin",
            "main",
        ]
    )

    print("\nPASS: Phase Four commit pushed successfully.")


def main():
    print("=" * 72)
    print("ESC Opportunity Finder — Phase Four " "participant-country index")
    print("=" * 72)

    print("""This update will:
  - preserve the existing background scraper architecture
  - preserve the hourly GitHub Actions workflow
  - preserve the canonical opportunity cache
  - normalize legacy participant-country cache values safely
  - build a country-agnostic participant-country index
  - index opportunities by stable opportunity ID
  - publish the index to both data/ and web/
  - make backend country search use the index
  - retain direct country matching for validation
  - validate index/cache consistency
  - validate Morocco through the generic MA index entry
  - validate multiple countries exist in the index
  - run backend and Python validation
  - selectively commit and push only Phase Four files
""")

    try:
        require_files()
        check_git_state()
        check_branch()
        check_remote()

        validate_scraper()
        validate_hourly_workflow()

        canonical_data = load_canonical_cache()
        published_data = load_published_cache()

        validate_canonical_published_ids(
            canonical_data,
            published_data,
        )

        print("\nNormalizing canonical participant-country values...")

        canonical_data, unmapped = normalize_opportunity_country_values(canonical_data)

        if unmapped:
            print(
                "WARNING: some participant-country values "
                "could not be mapped to ISO-style codes."
            )
            print("They remain recorded in " "eligible_countries_unmapped.")

        atomic_write_json(
            CANONICAL_CACHE,
            canonical_data,
        )

        # Keep the published opportunity cache synchronized with the
        # normalized canonical cache. This is deliberately done before
        # generating the index so both sources use exactly the same
        # participant-country representation.
        atomic_write_json(
            PUBLISHED_CACHE,
            canonical_data,
        )

        index = build_participant_country_index(canonical_data)

        validate_index(
            index,
            canonical_data,
        )

        validate_morocco_index(index)

        publish_index(index)

        validate_published_index()

        update_manifest(
            canonical_data,
            index,
        )

        update_backend_cache()
        update_backend_search()
        update_backend_tests()

        validate_index_against_published_cache()
        validate_country_independence()
        validate_frontend_compatibility()

        validate_python()
        run_backend_tests()
        validate_country_search()

        whitespace_check()

        selective_commit_and_push()

        print("\n" + "=" * 72)
        print("PHASE FOUR COMPLETE")
        print("=" * 72)

        print()
        print(
            "The participant-country index is now the " "backend search lookup layer."
        )

    except Exception as exc:
        print("\n" + "=" * 72)
        print("UPDATE FAILED")
        print("=" * 72)
        print()
        print(str(exc))
        print()
        print("No commit or push was performed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
