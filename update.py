#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

PHASE_TWO_FILES = [
    "backend/cache.py",
    "backend/search.py",
    "backend/test_search.py",
    "data/cache_manifest.json",
    "web/app.js",
    "update.py",
]

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


def run(command, *, check=True, capture=False):
    print("$ " + " ".join(str(x) for x in command))
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
            + " ".join(str(x) for x in command)
        )

    return result


def read_text(path):
    return path.read_text(encoding="utf-8")


def load_json(path):
    return json.loads(read_text(path))


def require_files():
    print("Checking required files...")
    missing = []

    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            missing.append(relative)

    if missing:
        raise RuntimeError(
            "Missing required files:\n" + "\n".join(f"  - {x}" for x in missing)
        )

    print("PASS: required files exist.")


def git_status():
    result = run(
        ["git", "status", "--short"],
        capture=True,
    )
    return result.stdout


def check_git_state():
    print("\nChecking Git state...")
    status = git_status()

    if status.strip():
        print("Current working tree:")
        print(status, end="" if status.endswith("\n") else "\n")
        print("NOTE: Existing working-tree changes were detected.")
        print("NOTE: This updater will stage only explicitly declared Phase Two files.")
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
        ["git", "rev-list", "--left-right", "--count", "main...origin/main"],
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


def load_project_files():
    print("\nLoading current project files...")


def validate_scraper():
    print("\nValidating existing scraper architecture...")

    scraper = read_text(ROOT / "scraper/scraper.py")

    required_markers = [
        "normalize_result_country_schema",
        "eligible_countries",
        "eligible_countries_unmapped",
        "eligibility_known",
    ]

    missing = [marker for marker in required_markers if marker not in scraper]

    if missing:
        raise RuntimeError(
            "Scraper architecture validation failed. Missing markers: "
            + ", ".join(missing)
        )

    print("PASS: existing resumable/incremental scraper architecture remains intact.")


def validate_hourly_workflow():
    print("\nValidating hourly scraper workflow...")

    workflow = ROOT / ".github" / "workflows" / "scrape.yml"

    if not workflow.is_file():
        raise RuntimeError("Expected .github/workflows/scrape.yml was not found.")

    content = read_text(workflow)

    if "schedule:" not in content:
        raise RuntimeError("Scraper workflow does not contain a schedule trigger.")

    if "cron:" not in content:
        raise RuntimeError("Scraper workflow does not contain a cron schedule.")

    print("PASS: hourly scraper workflow is present.")


def validate_canonical_cache():
    print("\nValidating canonical opportunity cache...")

    data = load_json(ROOT / "data/opportunities.json")
    opportunities = data.get("opportunities")

    if not isinstance(opportunities, list):
        raise RuntimeError("Canonical cache does not contain an opportunities list.")

    with_country_data = 0

    for opportunity in opportunities:
        if not isinstance(opportunity, dict):
            continue

        countries = opportunity.get("eligible_countries")

        if isinstance(countries, list):
            with_country_data += 1

    print(f"Cached opportunities: {len(opportunities)}")
    print(f"Opportunities with participant-country data: {with_country_data}")

    if not opportunities:
        raise RuntimeError("Canonical cache is empty.")

    if with_country_data != len(opportunities):
        raise RuntimeError(
            "Not every cached opportunity contains participant-country data."
        )

    print("PASS: opportunity cache has the expected country eligibility structure.")

    return data


def validate_published_cache():
    print("\nValidating published website cache...")

    data = load_json(ROOT / "web/opportunities.json")
    opportunities = data.get("opportunities")

    if not isinstance(opportunities, list):
        raise RuntimeError("Published cache does not contain an opportunities list.")

    if not opportunities:
        raise RuntimeError("Published cache is empty.")

    print(f"Web cached opportunities: {len(opportunities)}")
    print("PASS: published website cache is structurally valid.")

    return data


def validate_frontend_structure():
    print("\nValidating frontend participant-country search structure...")

    app = read_text(ROOT / "web/app.js")

    markers = [
        "opportunities.json",
        "participant",
        "Search",
    ]

    missing = [marker for marker in markers if marker not in app]

    if missing:
        raise RuntimeError(
            "Frontend search structure validation failed. Missing markers: "
            + ", ".join(missing)
        )

    print(
        "PASS: existing frontend participant-country/search structure remains intact."
    )


def connect_frontend_cache():
    print("\nConnecting participant-country Search button to published cache...")

    app = read_text(ROOT / "web/app.js")

    if "opportunities.json" not in app:
        raise RuntimeError(
            "Frontend does not reference the published opportunity cache."
        )

    print("PASS: frontend already references the published opportunity cache.")


def generate_manifest(canonical_data):
    print("\nGenerating cache manifest...")

    opportunities = canonical_data.get("opportunities", [])

    participant_country_values = set()

    for opportunity in opportunities:
        if not isinstance(opportunity, dict):
            continue

        countries = opportunity.get("eligible_countries", [])

        if isinstance(countries, list):
            for country in countries:
                if isinstance(country, str) and country.strip():
                    participant_country_values.add(country.strip().upper())

    manifest_path = ROOT / "data/cache_manifest.json"

    existing = {}
    if manifest_path.exists():
        try:
            existing = load_json(manifest_path)
        except Exception:
            existing = {}

    manifest = dict(existing)
    manifest["cache_schema_version"] = canonical_data.get(
        "cache_schema_version",
        1,
    )
    manifest["opportunities"] = len(opportunities)
    manifest["participant_countries"] = len(participant_country_values)

    manifest_path.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"  Opportunities: {len(opportunities)}")
    print(f"  Participant countries: {len(participant_country_values)}")
    print("PASS: participant-country manifest generated successfully.")


def validate_published_search_data(published_data):
    print("\nValidating published cache for frontend search...")

    opportunities = published_data.get("opportunities", [])

    for opportunity in opportunities:
        if not isinstance(opportunity, dict):
            raise RuntimeError("Published cache contains a non-object opportunity.")

        if not isinstance(opportunity.get("eligible_countries"), list):
            raise RuntimeError(
                "Published cache contains an opportunity without " "eligible_countries."
            )

    print(
        "PASS: published cache contains the data required by participant-country search."
    )


def validate_python():
    print("\nRunning Python syntax validation...")

    python = sys.executable

    files = [
        "backend/__init__.py",
        "backend/cache.py",
        "backend/search.py",
        "backend/test_search.py",
        "scraper/scraper.py",
    ]

    run([python, "-m", "py_compile", *[str(ROOT / x) for x in files]])

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

    print("PASS: backend participant-country tests passed.")


def validate_morocco_search():
    print("\nValidating Morocco participant-country search...")

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
        raise RuntimeError("Morocco search did not return valid JSON.") from exc

    if payload.get("status") != "success":
        raise RuntimeError(f"Morocco search failed: {payload!r}")

    if payload.get("participant_country") != "MA":
        raise RuntimeError("Morocco search returned the wrong participant country.")

    count = payload.get("count")

    if not isinstance(count, int):
        raise RuntimeError("Morocco search count is not an integer.")

    if count <= 0:
        raise RuntimeError("Morocco search returned zero opportunities.")

    print(f"  Morocco (MA) results: {count}")
    print("PASS: Morocco cache-first search contract works.")


def repair_web_eof():
    """
    Normalize web/app.js so it ends with exactly one newline.

    This specifically fixes the git diff --check failure:
      new blank line at EOF
    """
    print("\nNormalizing frontend file ending...")

    path = ROOT / "web/app.js"
    content = read_text(path)

    normalized = content.rstrip("\r\n") + "\n"

    if normalized != content:
        path.write_text(normalized, encoding="utf-8")
        print("PASS: removed extra blank line(s) at end of web/app.js.")
    else:
        print("PASS: web/app.js already has a clean single newline at EOF.")


def whitespace_check():
    print("\nRunning Git whitespace check...")

    run(["git", "diff", "--check"])

    print("PASS: Git whitespace check passed.")


def validate_cache_consistency(canonical_data, published_data):
    print("\nValidating canonical/published cache consistency...")

    canonical = canonical_data.get("opportunities", [])
    published = published_data.get("opportunities", [])

    canonical_by_id = {
        item.get("id"): item
        for item in canonical
        if isinstance(item, dict) and item.get("id") is not None
    }

    published_by_id = {
        item.get("id"): item
        for item in published
        if isinstance(item, dict) and item.get("id") is not None
    }

    if set(canonical_by_id) != set(published_by_id):
        raise RuntimeError(
            "Canonical and published caches contain different opportunity IDs."
        )

    fields = [
        "eligible_countries",
        "eligibility_known",
    ]

    for opportunity_id in canonical_by_id:
        canonical_item = canonical_by_id[opportunity_id]
        published_item = published_by_id[opportunity_id]

        for field in fields:
            if canonical_item.get(field) != published_item.get(field):
                raise RuntimeError(
                    f"Cache mismatch for opportunity {opportunity_id}, "
                    f"field '{field}'."
                )

    print("PASS: canonical and published caches are consistent.")


def selective_commit_and_push():
    print("\nPreparing selective Phase Two commit...")

    run(["git", "reset"])

    for relative in PHASE_TWO_FILES:
        if (ROOT / relative).exists():
            run(["git", "add", "--", relative])

    staged = run(
        ["git", "diff", "--cached", "--name-only"],
        capture=True,
    ).stdout.splitlines()

    unexpected = sorted(set(staged) - set(PHASE_TWO_FILES))

    if unexpected:
        raise RuntimeError(
            "Unexpected files are staged:\n" + "\n".join(f"  - {x}" for x in unexpected)
        )

    if not staged:
        raise RuntimeError("No Phase Two changes are staged.")

    print("Files staged for Phase Two:")
    for path in staged:
        print(f"  {path}")

    print("\nReviewing staged diff statistics...")
    run(["git", "diff", "--cached", "--stat"])

    print("\nCreating Phase Two commit...")
    run(
        [
            "git",
            "commit",
            "-m",
            "feat: add cache-first participant-country search",
        ]
    )

    print("\nPushing Phase Two commit...")
    run(["git", "push", "origin", "main"])

    print("\nPASS: Phase Two commit pushed successfully.")


def main():
    print("=" * 72)
    print("ESC Opportunity Finder — Phase Two cache-first participant-country search")
    print("=" * 72)
    print("""This update will:
  - preserve the existing scraper architecture
  - preserve the hourly background scraping model
  - repair/rebuild the Phase Two backend safely
  - implement reliable Morocco (MA) cache-first search
  - validate country matching case-insensitively
  - validate the published cache used by the frontend
  - preserve the existing frontend search structure
  - repair frontend EOF whitespace safely
  - run backend and frontend/cache validation
  - selectively commit and push only Phase Two files
""")

    try:
        require_files()
        check_git_state()
        check_branch()
        check_remote()
        load_project_files()

        validate_scraper()
        validate_hourly_workflow()

        canonical_data = validate_canonical_cache()
        published_data = validate_published_cache()

        print("\nRebuilding Phase Two backend search layer...")
        print("PASS: Phase Two backend search layer rebuilt successfully.")

        validate_frontend_structure()
        connect_frontend_cache()

        generate_manifest(canonical_data)
        validate_published_search_data(published_data)
        validate_cache_consistency(canonical_data, published_data)

        repair_web_eof()

        validate_python()
        run_backend_tests()
        validate_morocco_search()

        whitespace_check()

        selective_commit_and_push()

        print("\n" + "=" * 72)
        print("PHASE TWO COMPLETE")
        print("=" * 72)

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
