#!/usr/bin/env python3

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ============================================================================
# PROJECT PATHS
# ============================================================================

ROOT = Path(__file__).resolve().parent

DATA_DIR = ROOT / "data"
WEB_DIR = ROOT / "web"
BACKEND_DIR = ROOT / "backend"

SCRAPER_FILE = ROOT / "scraper" / "scraper.py"

OPPORTUNITIES_FILE = DATA_DIR / "opportunities.json"
WEB_OPPORTUNITIES_FILE = WEB_DIR / "opportunities.json"
CACHE_MANIFEST = DATA_DIR / "cache_manifest.json"


# ============================================================================
# CONSTANTS
# ============================================================================

CACHE_SCHEMA_VERSION = 1


# ============================================================================
# OUTPUT HELPERS
# ============================================================================


def banner(text):
    print()
    print("=" * 72)
    print(text)
    print("=" * 72)


def section(text):
    print()
    print(text)


def passed(text):
    print(f"PASS: {text}")


def note(text):
    print(f"NOTE: {text}")


def fail(text):
    print()
    print("=" * 72)
    print("UPDATE FAILED")
    print("=" * 72)
    print()
    print(text)
    print()
    print("No commit or push was performed.")
    raise SystemExit(1)


def run_command(command, check=True):
    print("$ " + " ".join(str(x) for x in command))

    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    if result.stdout:
        print(result.stdout.rstrip())

    if result.stderr:
        print(result.stderr.rstrip())

    if check and result.returncode != 0:
        fail(
            "Command failed with exit code "
            f"{result.returncode}: {' '.join(str(x) for x in command)}"
        )

    return result


# ============================================================================
# FILE HELPERS
# ============================================================================


def write_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_suffix(path.suffix + ".tmp")

    temporary.write_text(
        content,
        encoding="utf-8",
    )

    temporary.replace(path)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_suffix(path.suffix + ".tmp")

    temporary.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary.replace(path)


# ============================================================================
# GIT / SAFETY
# ============================================================================


def validate_git_state():
    section("Checking Git state...")

    result = run_command(
        ["git", "status", "--short"],
        check=True,
    )

    status = result.stdout.strip()

    if not status:
        passed("working tree is clean.")
        return

    lines = [line for line in status.splitlines() if line.strip()]

    allowed = {
        "update.py",
    }

    unexpected = []

    for line in lines:
        path = line[3:].strip()

        if path not in allowed:
            unexpected.append(line)

    if unexpected:
        print("Current working tree:")
        print(status)
        note("Existing changes outside update.py were detected.")
        note("They will not be overwritten by this update.")

    else:
        print("Current working tree:")
        print(status)
        passed("the only existing change is update.py.")


def validate_branch_and_remote():
    section("Checking branch...")

    result = run_command(
        ["git", "branch", "--show-current"],
    )

    branch = result.stdout.strip()

    if branch != "main":
        fail(f"Expected branch 'main', found '{branch}'.")

    passed("current branch is main.")

    section("Checking remote safety...")

    run_command(
        ["git", "fetch", "origin", "main"],
    )

    result = run_command(
        [
            "git",
            "rev-list",
            "--left-right",
            "--count",
            "main...origin/main",
        ],
    )

    values = result.stdout.strip().split()

    if len(values) != 2:
        fail("Could not determine local/remote commit state.")

    local_only = int(values[0])
    remote_only = int(values[1])

    print(f"Local-only commits: {local_only}")
    print(f"Remote-only commits: {remote_only}")

    if local_only != 0 or remote_only != 0:
        fail("Local main and origin/main are not synchronized.")

    passed("local main is synchronized with origin/main.")


# ============================================================================
# REQUIRED FILES
# ============================================================================


def validate_required_files():
    required = [
        DATA_DIR,
        WEB_DIR,
        SCRAPER_FILE,
        OPPORTUNITIES_FILE,
        WEB_OPPORTUNITIES_FILE,
    ]

    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]

    if missing:
        fail(
            "Missing required project files/directories:\n"
            + "\n".join(f"  - {item}" for item in missing)
        )

    passed("required files exist.")


# ============================================================================
# DATA VALIDATION
# ============================================================================


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"Could not read {path.relative_to(ROOT)} as JSON: {exc}")


def validate_opportunity_dataset():
    section("Validating current opportunity cache...")

    data = load_json(OPPORTUNITIES_FILE)

    if not isinstance(data, dict):
        fail("data/opportunities.json must contain a JSON object.")

    opportunities = data.get("opportunities")

    if not isinstance(opportunities, list):
        fail("data/opportunities.json does not contain " "an opportunities list.")

    valid = 0

    for index, opportunity in enumerate(opportunities):
        if not isinstance(opportunity, dict):
            fail("Invalid opportunity at index " f"{index}: expected an object.")

        if not opportunity.get("id"):
            fail("Opportunity at index " f"{index} has no id/opid.")

        eligible = opportunity.get("eligible_countries")

        if eligible is None:
            fail(
                "Opportunity "
                f"{opportunity.get('id')} is missing "
                "eligible_countries."
            )

        if not isinstance(eligible, list):
            fail(
                "Opportunity "
                f"{opportunity.get('id')} has a non-list "
                "eligible_countries value."
            )

        valid += 1

    if "eligible_countries" not in opportunities[0] if opportunities else False:
        fail("The cache does not expose eligible_countries.")

    passed(f"cache contains {valid} structurally valid opportunities.")

    return data


def validate_web_dataset():
    section("Validating published website cache...")

    web_data = load_json(WEB_OPPORTUNITIES_FILE)

    if not isinstance(web_data, dict):
        fail("web/opportunities.json must contain a JSON object.")

    opportunities = web_data.get("opportunities")

    if not isinstance(opportunities, list):
        fail("web/opportunities.json does not contain " "an opportunities list.")

    passed(f"web cache contains {len(opportunities)} opportunities.")


def validate_existing_scraper():
    section("Validating existing scraper architecture...")

    if not SCRAPER_FILE.exists():
        fail("scraper/scraper.py is missing.")

    source = SCRAPER_FILE.read_text(encoding="utf-8")

    required_markers = [
        "CHECKPOINT_SCHEMA_VERSION",
        "DETAIL_RECHECK_INTERVAL",
        "eligible_countries",
        "checkpoint",
        "opportunities.json",
        "expired.json",
    ]

    missing = [marker for marker in required_markers if marker not in source]

    if missing:
        fail(
            "Existing scraper architecture appears incomplete. "
            "Missing markers:\n" + "\n".join(f"  - {item}" for item in missing)
        )

    passed("existing resumable/incremental scraper architecture remains intact.")


# ============================================================================
# CACHE MANIFEST
# ============================================================================


def build_manifest(data):
    opportunities = data.get(
        "opportunities",
        [],
    )

    countries = set()

    for opportunity in opportunities:
        if not isinstance(opportunity, dict):
            continue

        eligible = opportunity.get(
            "eligible_countries",
            [],
        )

        if not isinstance(eligible, list):
            continue

        for value in eligible:
            if not isinstance(value, str):
                continue

            code = value.strip().upper()

            if len(code) == 2:
                countries.add(code)

    generated_at = data.get("generated_at") or data.get("last_updated")

    manifest_generated_at = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    return {
        "schema_version": CACHE_SCHEMA_VERSION,
        "generated_at": generated_at,
        "manifest_generated_at": manifest_generated_at,
        "opportunity_count": len(opportunities),
        "participant_country_count": len(countries),
        "participant_countries": sorted(countries),
        "source": "data/opportunities.json",
    }


def write_cache_manifest(data):
    section("Generating cache manifest...")

    manifest = build_manifest(data)

    write_json(
        CACHE_MANIFEST,
        manifest,
    )

    passed("data/cache_manifest.json generated.")

    print(f"  Opportunities: " f"{manifest['opportunity_count']}")

    print(f"  Participant countries: " f"{manifest['participant_country_count']}")


# ============================================================================
# BACKEND FILE CONTENT
# ============================================================================

BACKEND_INIT_CONTENT = """# ESC Opportunity Finder backend package.

__all__ = [
    "cache",
    "search",
]
"""


BACKEND_CACHE_CONTENT = """import json
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
"""


BACKEND_SEARCH_CONTENT = """import json
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
    raise SystemExit(main())
"""


BACKEND_TEST_CONTENT = """import unittest

from .cache import (
    load_cache,
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

    def test_search_returns_expected_shape(self):
        payload = search_cache("MA")

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


if __name__ == "__main__":
    unittest.main()
"""


BACKEND_README_CONTENT = """# ESC Opportunity Finder Backend

This directory contains the first cache-first backend foundation.

## Architecture

The scraper remains responsible for collecting and incrementally updating
the canonical opportunity dataset:

    data/opportunities.json

The backend does not scrape the ESC portal for every user search.

Instead, the request flow is:

    User
      |
      v
    Search API
      |
      v
    Backend cache
      |
      v
    data/opportunities.json

The scheduled GitHub Actions scraper keeps the cache fresh.

## Files

### cache.py

Provides the cache abstraction.

Responsibilities:

- load the canonical opportunity cache
- validate the basic cache structure
- normalize participant country codes
- filter opportunities by participant country
- expose cache metadata

### search.py

Provides a command-line search service for the current development phase.

Example:

    python -m backend.search MA

The command returns JSON.

### test_search.py

Contains basic backend/cache tests.

## Cache strategy

The canonical dataset remains:

    data/opportunities.json

The website copy remains:

    web/opportunities.json

The manifest is:

    data/cache_manifest.json

The manifest provides lightweight metadata without requiring consumers to
load the entire opportunity dataset.

## Important design decision

The participant-country search currently operates entirely against the cache.

It does not make live ESC API requests.

This gives us:

- fast searches
- predictable response times
- no ESC API dependency during a user request
- protection against request spikes
- simpler error handling
- a clear separation between ingestion and serving

The next phase can add an HTTP service around `backend.search`.

Only after that service is stable should the frontend Search action be connected
to it.

## Future refresh model

The scheduled scraper should remain the ingestion mechanism.

Its responsibility is to:

1. discover current ESC opportunities
2. compare them with the checkpoint/cache
3. fetch detail pages when necessary
4. update existing opportunities when their relevant data changes
5. remove or archive opportunities that are no longer active
6. publish the resulting canonical JSON

The frontend/backend serving path should never need to perform a full scrape.

## Reliability model

The scraper and the search service are intentionally separated.

A temporary ESC API outage should not make the cached search unavailable.

A user search should continue returning the most recently successful cache.

The cache should therefore be treated as a durable snapshot rather than a
temporary intermediate result.
"""


# ============================================================================
# BACKEND INSTALLATION
# ============================================================================


def install_backend_files():
    section("Creating backend/cache layer...")

    BACKEND_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    write_text(
        BACKEND_DIR / "__init__.py",
        BACKEND_INIT_CONTENT,
    )

    write_text(
        BACKEND_DIR / "cache.py",
        BACKEND_CACHE_CONTENT,
    )

    write_text(
        BACKEND_DIR / "search.py",
        BACKEND_SEARCH_CONTENT,
    )

    write_text(
        BACKEND_DIR / "test_search.py",
        BACKEND_TEST_CONTENT,
    )

    write_text(
        BACKEND_DIR / "README.md",
        BACKEND_README_CONTENT,
    )

    passed("backend cache/search foundation created.")


# ============================================================================
# VALIDATION
# ============================================================================


def run_python_compile_check():
    section("Running Python syntax validation...")

    files = [
        BACKEND_DIR / "__init__.py",
        BACKEND_DIR / "cache.py",
        BACKEND_DIR / "search.py",
        BACKEND_DIR / "test_search.py",
        SCRAPER_FILE,
    ]

    run_command(
        [
            sys.executable,
            "-m",
            "py_compile",
            *[str(path) for path in files],
        ]
    )

    passed("Python syntax validation passed.")


def run_backend_tests():
    section("Running backend tests...")

    run_command(
        [
            sys.executable,
            "-m",
            "unittest",
            "backend.test_search",
            "-v",
        ]
    )

    passed("backend cache tests passed.")


def run_cache_search_smoke_test():
    section("Running cache search smoke test...")

    result = run_command(
        [
            sys.executable,
            "-m",
            "backend.search",
            "MA",
        ],
        check=True,
    )

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        fail("backend.search did not return valid JSON: " f"{exc}")

    if payload.get("status") != "success":
        fail("backend.search returned an unexpected status.")

    if payload.get("participant_country") != "MA":
        fail("backend.search returned the wrong " "participant country.")

    if not isinstance(
        payload.get("opportunities"),
        list,
    ):
        fail("backend.search did not return an " "opportunities list.")

    passed("participant-country cache search works.")

    print(f"  Cached MA results: " f"{payload.get('count', 0)}")


def run_git_checks():
    section("Running Git whitespace check...")

    run_command(
        [
            "git",
            "diff",
            "--check",
        ]
    )

    passed("git diff --check passed.")


def show_diff():
    section("Reviewing backend/cache diff...")

    run_command(
        [
            "git",
            "diff",
            "--",
            "backend",
            "data/cache_manifest.json",
        ],
        check=False,
    )


# ============================================================================
# MAIN
# ============================================================================


def main():
    banner("ESC Opportunity Finder — cache-first backend foundation")

    section("Checking required files...")
    validate_required_files()

    validate_git_state()

    validate_branch_and_remote()

    section("Loading current project files...")

    data = validate_opportunity_dataset()

    validate_web_dataset()

    validate_existing_scraper()

    install_backend_files()

    write_cache_manifest(data)

    run_python_compile_check()

    run_backend_tests()

    run_cache_search_smoke_test()

    run_git_checks()

    show_diff()

    print()
    print("=" * 72)
    print("UPDATE COMPLETE")
    print("=" * 72)
    print()

    print("Implemented:")
    print()
    print("  1. Canonical cache metadata")
    print("     data/cache_manifest.json")
    print()
    print("  2. Cache abstraction")
    print("     backend/cache.py")
    print()
    print("  3. Participant-country search service")
    print("     backend/search.py")
    print()
    print("  4. Backend tests")
    print("     backend/test_search.py")
    print()
    print("  5. Backend architecture documentation")
    print("     backend/README.md")
    print()
    print("  6. Existing scraper architecture preserved")
    print()
    print("Test manually with:")
    print()
    print("  python -m backend.search MA")
    print()
    print(
        "The next implementation phase should add the HTTP service "
        "and then connect the frontend Search action to it."
    )
    print()
    print("No commit or push was performed.")


if __name__ == "__main__":
    main()
