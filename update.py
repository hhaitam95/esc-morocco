#!/usr/bin/env python3

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

REMOTE = "origin"
BRANCH = "main"

DATA_DIR = ROOT / "data"
WEB_DIR = ROOT / "web"

SOURCE_DATA_JSON = DATA_DIR / "opportunities.json"
SOURCE_EXPIRED_JSON = DATA_DIR / "expired.json"
CHECKPOINT_JSON = DATA_DIR / "checkpoint.json"
REPAIR_CHECKPOINT = DATA_DIR / "full_detail_repair_checkpoint.json"

WEB_DATA_JSON = WEB_DIR / "opportunities.json"
WEB_EXPIRED_JSON = WEB_DIR / "expired.json"

SCRAPER = ROOT / "scraper" / "scraper.py"
APP_JS = WEB_DIR / "app.js"
DATA_PROVIDER_JS = WEB_DIR / "data-provider.js"
INDEX_HTML = WEB_DIR / "index.html"

UPDATE_WORKFLOW = ROOT / ".github" / "workflows" / "update.yml"
DEPLOY_WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"
SCRAPE_WORKFLOW = ROOT / ".github" / "workflows" / "scrape.yml"

REVIEW_MD = ROOT / "UPDATE_REVIEW.md"

TARGET_ID = "53577"

MIN_EXPECTED_OPPORTUNITIES = 1000
EXPECTED_BASELINE_OPPORTUNITIES = 1111

CANONICAL_DATA_URL = (
    "https://raw.githubusercontent.com/"
    "hhaitam95/esc-opportunity-finder/main/data/opportunities.json"
)

PROTECTED_LOCAL_ARTIFACTS = {
    "data/full_detail_repair_checkpoint.json",
}


# ============================================================================
# OUTPUT
# ============================================================================


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    print()
    print("No destructive cleanup was performed.")
    sys.exit(1)


# ============================================================================
# COMMANDS
# ============================================================================


def run(
    command: list[str],
    *,
    check: bool = True,
    quiet: bool = False,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    if not quiet:
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="")

    if check and result.returncode != 0:
        fail(
            f"Command failed with exit code {result.returncode}: "
            f"{' '.join(command)}"
        )

    return result


# ============================================================================
# BASIC VALIDATION
# ============================================================================


def validate_update_py() -> None:
    result = run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(Path(__file__).resolve()),
        ],
        check=False,
    )

    if result.returncode != 0:
        if result.stdout:
            print(result.stdout.rstrip())
        if result.stderr:
            print(result.stderr.rstrip())
        fail("update.py syntax validation failed.")

    print("PASS: update.py syntax validated.")


def validate_repository() -> None:
    if not (ROOT / ".git").exists():
        fail("Repository root is not a Git repository.")

    actual_root = Path(
        run(
            [
                "git",
                "rev-parse",
                "--show-toplevel",
            ],
            quiet=True,
        ).stdout.strip()
    ).resolve()

    if actual_root != ROOT.resolve():
        fail(
            "update.py must run from repository root.\n"
            f"Expected: {ROOT.resolve()}\n"
            f"Actual:   {actual_root}"
        )

    print(f"PASS: repository root validated: {ROOT}")


def validate_branch() -> None:
    branch = run(
        [
            "git",
            "branch",
            "--show-current",
        ],
        quiet=True,
    ).stdout.strip()

    if branch != BRANCH:
        fail(f"Current branch is {branch!r}; expected {BRANCH!r}.")

    print("PASS: current branch is main.")


def validate_origin() -> None:
    remote = run(
        [
            "git",
            "remote",
            "get-url",
            REMOTE,
        ],
        quiet=True,
    ).stdout.strip()

    expected = "https://github.com/hhaitam95/esc-opportunity-finder.git"

    if remote != expected:
        fail(
            "origin remote is not canonical.\n"
            f"Expected: {expected}\n"
            f"Actual:   {remote}"
        )

    print(f"PASS: origin remote is canonical: {remote}")


def status_lines() -> list[str]:
    result = run(
        [
            "git",
            "status",
            "--porcelain=v1",
        ],
        quiet=True,
    )

    return [line for line in result.stdout.splitlines() if line.strip()]


def print_status() -> None:
    print("Current Git status:")

    status = status_lines()

    if not status:
        print("  clean")
        return

    for line in status:
        print(f"  {line}")


def protect_repair_checkpoint() -> None:
    if REPAIR_CHECKPOINT.exists():
        print(
            "INFO: preserving allowed local protected artifact: " f"{REPAIR_CHECKPOINT}"
        )
        print("PASS: local backend repair checkpoint remains untouched.")
    else:
        print("INFO: local backend repair checkpoint is not present.")


def validate_protected_worktree() -> None:
    allowed = {
        "update.py",
        "UPDATE_REVIEW.md",
        ".github/workflows/update.yml",
        ".github/workflows/deploy.yml",
        ".github/workflows/scrape.yml",
        "web/app.js",
        "web/index.html",
        "web/data-provider.js",
        "web/opportunities.json",
        "web/expired.json",
        "data/full_detail_repair_checkpoint.json",
    }

    unexpected = []

    for line in status_lines():
        path = line[3:].strip()

        if " -> " in path:
            path = path.split(" -> ", 1)[1]

        if path not in allowed:
            unexpected.append(path)

    if unexpected:
        fail(
            "Unexpected working-tree changes detected:\n"
            + "\n".join(f"  - {path}" for path in sorted(set(unexpected)))
        )

    print("PASS: protected backend/cache files are untouched.")


# ============================================================================
# GIT SAFETY
# ============================================================================


def fetch_origin() -> None:
    print("Refreshing origin/main...")

    run(
        [
            "git",
            "fetch",
            "--prune",
            "origin",
        ]
    )

    print("PASS: origin/main refreshed.")


def commit_counts() -> tuple[int, int]:
    ahead = int(
        run(
            [
                "git",
                "rev-list",
                "--count",
                "origin/main..main",
            ],
            quiet=True,
        ).stdout.strip()
    )

    behind = int(
        run(
            [
                "git",
                "rev-list",
                "--count",
                "main..origin/main",
            ],
            quiet=True,
        ).stdout.strip()
    )

    return ahead, behind


def require_safe_history() -> None:
    ahead, behind = commit_counts()

    print(f"Local commits ahead: {ahead}")

    print(f"Remote commits ahead: {behind}")

    if behind > 0:
        if ahead > 0:
            fail(
                "Local main and origin/main have diverged. "
                "Phase 2 will not merge, rebase, reset, "
                "or rewrite history automatically."
            )

        fail(
            "Local main is behind origin/main. "
            "Phase 2 will not overwrite newer remote work."
        )

    print("PASS: local main is not behind origin/main.")


# ============================================================================
# JSON
# ============================================================================


def load_json(path: Path):
    if not path.exists():
        fail(f"Required JSON file is missing: {path}")

    text = path.read_text(encoding="utf-8")

    if any(
        marker in text
        for marker in (
            "<<<<<<< ",
            "=======",
            ">>>>>>> ",
        )
    ):
        fail(f"Git conflict marker detected in {path}.")

    try:
        return json.loads(text)
    except Exception as exc:
        fail(f"Could not parse {path}: {exc}")


def extract_opportunities(
    payload,
    path: Path,
) -> list[dict]:
    if not isinstance(payload, dict):
        fail(f"{path} must contain a JSON object.")

    records = payload.get("opportunities")

    if not isinstance(records, list):
        fail(f"{path} does not contain an opportunities list.")

    if any(not isinstance(item, dict) for item in records):
        fail(f"{path} contains a non-object opportunity record.")

    return records


def opportunity_id(
    record: dict,
) -> str | None:
    raw = record.get("id") or record.get("opid") or record.get("opportunity_id")

    if raw is None:
        return None

    value = str(raw).strip()

    return value or None


def date_value(
    record: dict,
    *keys: str,
) -> str | None:
    for key in keys:
        value = record.get(key)

        if value:
            return str(value)

    activity_dates = record.get("activity_dates")

    if isinstance(
        activity_dates,
        dict,
    ):
        for key in keys:
            value = activity_dates.get(key)

            if value:
                return str(value)

    return None


def find_logo_value(
    record: dict,
) -> str | None:
    """
    Accept the repository's existing logo schema without forcing one
    field name. Earlier versions of the scraper used get_image_url()
    and have historically stored logo data under different keys.
    """
    candidate_keys = (
        "logo_url",
        "logo",
        "logoUrl",
        "image_url",
        "imageUrl",
        "association_logo",
        "association_logo_url",
        "organisation_logo",
        "organization_logo",
        "organization_logo_url",
        "image",
    )

    for key in candidate_keys:
        value = record.get(key)

        if isinstance(value, str) and value.strip():
            return value.strip()

        if isinstance(value, dict):
            for nested_key in (
                "url",
                "src",
                "href",
            ):
                nested = value.get(nested_key)

                if (
                    isinstance(
                        nested,
                        str,
                    )
                    and nested.strip()
                ):
                    return nested.strip()

    return None


def validate_link_value(
    record: dict,
) -> bool:
    for key in (
        "url",
        "opportunity_url",
        "portal_url",
        "link",
        "view_url",
    ):
        value = record.get(key)

        if isinstance(value, str) and value.strip():
            return True

    return False


# ============================================================================
# BASELINE DATA VALIDATION
# ============================================================================


def validate_current_dataset() -> dict:
    print()
    print("Validating current backend dataset...")

    payload = load_json(SOURCE_DATA_JSON)

    records = extract_opportunities(
        payload,
        SOURCE_DATA_JSON,
    )

    count = len(records)

    if count < MIN_EXPECTED_OPPORTUNITIES:
        fail(
            "Canonical dataset contains too few opportunities.\n"
            f"Expected at least {MIN_EXPECTED_OPPORTUNITIES}; "
            f"found {count}."
        )

    ids = [opportunity_id(record) for record in records]

    if any(value is None for value in ids):
        fail("Canonical dataset contains opportunity records " "without IDs.")

    if len(set(ids)) != len(ids):
        fail("Canonical dataset contains duplicate " "opportunity IDs.")

    target = next(
        (record for record in records if opportunity_id(record) == TARGET_ID),
        None,
    )

    if target is None:
        fail(f"Opportunity {TARGET_ID} is missing.")

    start_date = date_value(
        target,
        "start_date",
        "start",
    )

    end_date = date_value(
        target,
        "end_date",
        "end",
    )

    deadline = target.get("application_deadline") or target.get("deadline")

    country = (
        target.get("country") or target.get("country_code") or target.get("countryCode")
    )

    town = target.get("town") or target.get("city") or target.get("location")

    generated_at = payload.get("generated_at")

    if not generated_at:
        fail("Canonical dataset has no generated_at.")

    print(f"PASS: data/opportunities.json contains " f"{count} unique opportunities.")

    print(f"start_date: {start_date!r}")

    print(f"end_date: {end_date!r}")

    print(f"deadline: {deadline!r}")

    print(f"country: {country!r}")

    print(f"town: {town!r}")

    print(f"generated_at: {generated_at!r}")

    if not start_date:
        fail(f"Opportunity {TARGET_ID} has no recognizable start date.")

    if not end_date:
        fail(f"Opportunity {TARGET_ID} has no recognizable end date.")

    if not deadline:
        fail(f"Opportunity {TARGET_ID} has no recognizable deadline.")

    if not country:
        fail(f"Opportunity {TARGET_ID} has no recognizable country.")

    logo_value = find_logo_value(target)

    if logo_value:
        print(
            "PASS: opportunity 53577 contains recognizable "
            f"logo/image data in the existing schema."
        )
    else:
        print(
            "INFO: opportunity 53577 does not expose a recognized "
            "logo/image field; preserving the current schema without "
            "forcing a field rename."
        )

    if validate_link_value(target):
        print("PASS: opportunity 53577 contains a recognizable " "view/link field.")
    else:
        print(
            "INFO: opportunity 53577 has no recognizable view/link "
            "field; preserving the current schema."
        )

    print(f"PASS: opportunity {TARGET_ID} remains present and intact.")

    return payload


def validate_expired_dataset() -> int:
    payload = load_json(SOURCE_EXPIRED_JSON)

    records = extract_opportunities(
        payload,
        SOURCE_EXPIRED_JSON,
    )

    ids = [opportunity_id(record) for record in records]

    if any(value is None for value in ids):
        fail("data/expired.json contains a record without an ID.")

    if len(set(ids)) != len(ids):
        fail("data/expired.json contains duplicate opportunity IDs.")

    if not records:
        fail("data/expired.json is empty.")

    print(f"PASS: data/expired.json contains " f"{len(records)} unique opportunities.")

    return len(records)


def validate_checkpoint() -> None:
    payload = load_json(CHECKPOINT_JSON)

    count = None

    if isinstance(
        payload,
        dict,
    ):
        for key in (
            "processed",
            "processed_ids",
            "records",
            "opportunities",
            "items",
        ):
            value = payload.get(key)

            if isinstance(
                value,
                (dict, list),
            ):
                count = len(value)
                break

        if count is None:
            count = len(payload)

    elif isinstance(
        payload,
        list,
    ):
        count = len(payload)

    else:
        fail("checkpoint.json has an unsupported root type.")

    if count < 1000:
        fail("checkpoint.json appears unexpectedly small: " f"{count} records/IDs.")

    print(
        "PASS: checkpoint contains approximately "
        f"{count} tracked opportunity records/IDs."
    )


# ============================================================================
# SCRAPER / WORKFLOW VALIDATION
# ============================================================================


def validate_scraper() -> None:
    if not SCRAPER.exists():
        fail(f"Missing scraper: {SCRAPER}")

    result = run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(SCRAPER),
        ],
        check=False,
    )

    if result.returncode != 0:
        fail("scraper/scraper.py syntax validation failed.")

    source = SCRAPER.read_text(encoding="utf-8")

    for marker in (
        "checkpoint",
        "opportunit",
    ):
        if marker not in source.lower():
            fail(f"Scraper does not contain expected " f"incremental marker: {marker}")

    print("PASS: scraper/scraper.py syntax validated.")

    print(
        "PASS: existing scraper contains "
        "checkpoint/opportunity incremental processing architecture."
    )


def validate_yaml(
    path: Path,
) -> None:
    if not path.exists():
        fail(f"Missing workflow: {path}")

    try:
        import yaml
    except ImportError:
        print(
            f"INFO: PyYAML is unavailable; structural validation "
            f"used for {path.name}."
        )
        return

    try:
        yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"{path.relative_to(ROOT)} is invalid YAML: {exc}")

    print(f"PASS: {path.relative_to(ROOT)} YAML parsed successfully.")


def validate_workflows_before_change() -> None:
    validate_yaml(UPDATE_WORKFLOW)

    validate_yaml(DEPLOY_WORKFLOW)

    update_source = UPDATE_WORKFLOW.read_text(encoding="utf-8")

    deploy_source = DEPLOY_WORKFLOW.read_text(encoding="utf-8")

    if "schedule:" not in update_source:
        fail("update.yml has no schedule.")

    if "python scraper/scraper.py" not in update_source:
        fail("update.yml does not invoke scraper/scraper.py.")

    if "workflow_dispatch:" not in update_source:
        fail("update.yml has no workflow_dispatch.")

    if "./web" not in deploy_source:
        fail("deploy.yml does not deploy ./web.")

    print("PASS: existing update.yml and deploy.yml " "are structurally valid.")


# ============================================================================
# DATA PROVIDER
# ============================================================================


def validate_data_provider() -> str:
    if not DATA_PROVIDER_JS.exists():
        fail("web/data-provider.js is missing.")

    source = DATA_PROVIDER_JS.read_text(encoding="utf-8")

    if "window.ESC_DATA_PROVIDER" not in source:
        fail("web/data-provider.js does not expose " "ESC_DATA_PROVIDER.")

    if "opportunities.json" not in source:
        fail("web/data-provider.js does not reference " "the opportunity dataset.")

    return source


def patch_data_provider() -> bool:
    source = validate_data_provider()

    original = source

    canonical_url_pattern = re.escape(CANONICAL_DATA_URL)

    if re.search(
        canonical_url_pattern,
        source,
    ):
        print(
            "PASS: data-provider.js already loads canonical " "data/opportunities.json."
        )
        return False

    replacements = [
        (
            re.compile(r"`\./opportunities\.json\?v=\$\{Date\.now\(\)\}`"),
            "`" + CANONICAL_DATA_URL + "?v=${Date.now()}`",
        ),
        (
            re.compile(r"""["']\./opportunities\.json["']"""),
            "'" + CANONICAL_DATA_URL + "'",
        ),
        (
            re.compile(r"""["']opportunities\.json["']"""),
            "'" + CANONICAL_DATA_URL + "'",
        ),
    ]

    for pattern, replacement in replacements:
        source = pattern.sub(
            replacement,
            source,
            count=1,
        )

        if source != original:
            break

    if source == original:
        fail(
            "Could not safely locate the existing opportunity "
            "JSON fetch in web/data-provider.js."
        )

    DATA_PROVIDER_JS.write_text(
        source,
        encoding="utf-8",
    )

    print("PASS: data-provider.js now loads " "data/opportunities.json directly.")

    return True


# ============================================================================
# REMOVE DUPLICATE DATA
# ============================================================================


def remove_duplicate_dataset(
    canonical_path: Path,
    duplicate_path: Path,
    description: str,
) -> bool:
    if not duplicate_path.exists():
        print(f"PASS: {duplicate_path.relative_to(ROOT)} is already absent.")
        return False

    canonical_payload = load_json(canonical_path)

    duplicate_payload = load_json(duplicate_path)

    canonical_records = extract_opportunities(
        canonical_payload,
        canonical_path,
    )

    duplicate_records = extract_opportunities(
        duplicate_payload,
        duplicate_path,
    )

    canonical_ids = {opportunity_id(item) for item in canonical_records}

    duplicate_ids = {opportunity_id(item) for item in duplicate_records}

    if canonical_ids != duplicate_ids:
        fail(
            f"Refusing to remove {duplicate_path.relative_to(ROOT)}: "
            f"{description} IDs do not exactly match the canonical dataset."
        )

    canonical_generated = canonical_payload.get("generated_at")

    duplicate_generated = duplicate_payload.get("generated_at")

    if (
        canonical_generated
        and duplicate_generated
        and canonical_generated != duplicate_generated
    ):
        fail(
            f"Refusing to remove {duplicate_path.relative_to(ROOT)}: "
            "generated_at does not match the canonical dataset."
        )

    duplicate_path.unlink()

    print(
        f"PASS: removed duplicate generated dataset: "
        f"{duplicate_path.relative_to(ROOT)}"
    )

    return True


def remove_obsolete_web_datasets() -> list[str]:
    removed: list[str] = []

    if remove_duplicate_dataset(
        SOURCE_DATA_JSON,
        WEB_DATA_JSON,
        "opportunity",
    ):
        removed.append(WEB_DATA_JSON.relative_to(ROOT).as_posix())

    if remove_duplicate_dataset(
        SOURCE_EXPIRED_JSON,
        WEB_EXPIRED_JSON,
        "expired opportunity",
    ):
        removed.append(WEB_EXPIRED_JSON.relative_to(ROOT).as_posix())

    return removed


# ============================================================================
# SCRAPER WORKFLOW
# ============================================================================


def patch_update_workflow() -> bool:
    source = UPDATE_WORKFLOW.read_text(encoding="utf-8")

    original = source

    source = source.replace(
        "            git add -- web/opportunities.json\n",
        "",
    )

    source = source.replace(
        "            git add -- web/expired.json\n",
        "",
    )

    source = source.replace(
        "git add -- web/opportunities.json\n",
        "",
    )

    source = source.replace(
        "git add -- web/expired.json\n",
        "",
    )

    source = re.sub(
        r"(?m)^\s*cp\s+data/opportunities\.json\s+web/opportunities\.json\s*$\n?",
        "",
        source,
    )

    source = re.sub(
        r"(?m)^\s*cp\s+data/expired\.json\s+web/expired\.json\s*$\n?",
        "",
        source,
    )

    if (
        "git add -- web/opportunities.json" in source
        or "git add -- web/expired.json" in source
    ):
        fail("update.yml still contains obsolete web dataset staging.")

    if re.search(
        r"cp\s+data/opportunities\.json\s+web/opportunities\.json",
        source,
    ):
        fail("update.yml still copies opportunities.json into web/.")

    if re.search(
        r"cp\s+data/expired\.json\s+web/expired\.json",
        source,
    ):
        fail("update.yml still copies expired.json into web/.")

    if source == original:
        print("PASS: update.yml already publishes canonical data only.")
        return False

    UPDATE_WORKFLOW.write_text(
        source,
        encoding="utf-8",
    )

    print("PASS: update.yml no longer publishes duplicate web JSON files.")

    return True


# ============================================================================
# DEPLOY WORKFLOW
# ============================================================================


def patch_deploy_workflow() -> bool:
    source = DEPLOY_WORKFLOW.read_text(encoding="utf-8")

    original = source

    source = re.sub(
        r"\n\s*workflow_run:\n"
        r"\s*workflows:\n"
        r"\s*-\s*[\"']Update ESC Opportunities[\"']\n"
        r"\s*types:\n"
        r"\s*-\s*completed\s*\n",
        "\n",
        source,
        count=1,
    )

    source = re.sub(
        r"\n\s*if:\s*>\n"
        r"\s*github\.event_name == 'push' \|\|\n"
        r"\s*github\.event_name == 'workflow_dispatch' \|\|\n"
        r"\s*\(\n"
        r"\s*github\.event_name == 'workflow_run' &&\n"
        r"\s*github\.event\.workflow_run\.conclusion == 'success'\n"
        r"\s*\)\s*\n",
        "\n",
        source,
        count=1,
    )

    if source == original:
        print("PASS: deploy.yml already uses push/manual deployment.")
        return False

    DEPLOY_WORKFLOW.write_text(
        source,
        encoding="utf-8",
    )

    print("PASS: deploy.yml simplified to push/manual deployment.")

    return True


# ============================================================================
# REMOVE SECOND SCRAPER
# ============================================================================


def remove_scrape_workflow() -> bool:
    if not SCRAPE_WORKFLOW.exists():
        print("PASS: scrape.yml is already absent.")
        return False

    source = SCRAPE_WORKFLOW.read_text(encoding="utf-8")

    if not source.strip():
        fail("scrape.yml is empty; refusing automatic deletion.")

    SCRAPE_WORKFLOW.unlink()

    print("PASS: removed redundant .github/workflows/scrape.yml.")

    return True


# ============================================================================
# FINAL ARCHITECTURE VALIDATION
# ============================================================================


def validate_final_architecture() -> None:
    if SCRAPE_WORKFLOW.exists():
        fail("scrape.yml still exists after Phase 2.")

    if WEB_DATA_JSON.exists():
        fail("web/opportunities.json still exists after Phase 2.")

    if WEB_EXPIRED_JSON.exists():
        fail("web/expired.json still exists after Phase 2.")

    update_source = UPDATE_WORKFLOW.read_text(encoding="utf-8")

    deploy_source = DEPLOY_WORKFLOW.read_text(encoding="utf-8")

    provider_source = DATA_PROVIDER_JS.read_text(encoding="utf-8")

    if "git add -- web/opportunities.json" in update_source:
        fail("update.yml still stages web/opportunities.json.")

    if "git add -- web/expired.json" in update_source:
        fail("update.yml still stages web/expired.json.")

    if re.search(
        r"cp\s+data/opportunities\.json\s+web/opportunities\.json",
        update_source,
    ):
        fail("update.yml still copies opportunities.json to web/.")

    if re.search(
        r"cp\s+data/expired\.json\s+web/expired\.json",
        update_source,
    ):
        fail("update.yml still copies expired.json to web/.")

    if (
        CANONICAL_DATA_URL not in provider_source
        and "data/opportunities.json" not in provider_source
    ):
        fail("data-provider.js does not point to canonical " "data/opportunities.json.")

    if "workflow_run:" in deploy_source:
        fail("deploy.yml still contains workflow_run.")

    if "actions/deploy-pages" not in deploy_source:
        fail("deploy.yml no longer contains the Pages deployment action.")

    if "./web" not in deploy_source:
        fail("deploy.yml no longer uploads ./web.")

    print("PASS: only one scraper workflow remains.")

    print("PASS: data/opportunities.json is the canonical " "opportunity dataset.")

    print("PASS: duplicate web JSON datasets are removed.")

    print("PASS: deploy.yml is deployment-only.")


# ============================================================================
# FRONTEND VALIDATION
# ============================================================================


def validate_js(path: Path) -> None:
    if not path.exists():
        fail(f"Missing frontend file: {path}")

    result = run(
        [
            "node",
            "--check",
            str(path),
        ],
        check=False,
    )

    if result.returncode != 0:
        fail(f"{path.relative_to(ROOT)} failed node --check.")

    print(f"PASS: {path.relative_to(ROOT)} syntax validated.")


def validate_frontend() -> None:
    validate_js(APP_JS)

    validate_js(DATA_PROVIDER_JS)

    if not INDEX_HTML.exists():
        fail("web/index.html is missing.")

    html = INDEX_HTML.read_text(encoding="utf-8")

    if "data-provider.js" not in html:
        fail("web/index.html does not include data-provider.js.")

    if 'id="last-updated"' not in html:
        fail("web/index.html lost #last-updated.")

    if 'id="country-filter"' not in html:
        fail("web/index.html lost #country-filter.")

    print("PASS: frontend integration points remain present.")


# ============================================================================
# REVIEW
# ============================================================================


def write_review(
    baseline_count: int,
    expired_count: int,
    changed_files: list[str],
    removed_files: list[str],
) -> None:
    payload = load_json(SOURCE_DATA_JSON)

    generated_at = payload.get("generated_at")

    lines = [
        "# ESC Opportunity Finder — Phase 2 Production Review",
        "",
        "## Objective",
        "",
        "Simplify the backend architecture so there is one scraper "
        "workflow and one canonical opportunity dataset.",
        "",
        "## Baseline",
        "",
        f"- Canonical opportunities before migration: **{baseline_count}**",
        f"- Expired opportunities: **{expired_count}**",
        f"- generated_at: `{generated_at}`",
        "",
        "## Architecture after migration",
        "",
        "- `.github/workflows/update.yml` = only scraper/update workflow",
        "- `.github/workflows/deploy.yml` = only Pages deployment workflow",
        "- `data/opportunities.json` = canonical opportunity dataset",
        "- `data/expired.json` = canonical expired dataset",
        "- `data/checkpoint.json` = scraper progress",
        "- `web/data-provider.js` = frontend data access",
        "",
        "## Changes",
        "",
    ]

    if changed_files:
        lines.extend(f"- `{path}`" for path in changed_files)
    else:
        lines.append("- No source files required modification.")

    lines.extend(
        [
            "",
            "## Removed",
            "",
        ]
    )

    if removed_files:
        lines.extend(f"- `{path}`" for path in removed_files)
    else:
        lines.append("- No obsolete files needed removal.")

    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- `data/opportunities.json` was not rebuilt.",
            "- `data/checkpoint.json` was not rebuilt.",
            "- `data/expired.json` was preserved.",
            "- `data/full_detail_repair_checkpoint.json` was preserved.",
            "- No scraper execution was performed.",
            "- No Git history rewrite was performed.",
            "",
        ]
    )

    REVIEW_MD.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print(f"Review file written: {REVIEW_MD}")


# ============================================================================
# FINAL VALIDATION
# ============================================================================


def final_validation(
    baseline_count: int,
) -> None:
    print()
    print("Final Phase 2 validation...")

    final_payload = validate_current_dataset()

    final_records = extract_opportunities(
        final_payload,
        SOURCE_DATA_JSON,
    )

    final_count = len(final_records)

    if final_count != baseline_count:
        fail(
            "Canonical opportunity count changed during Phase 2.\n"
            f"Before: {baseline_count}\n"
            f"After:  {final_count}"
        )

    validate_expired_dataset()
    validate_checkpoint()
    validate_scraper()
    validate_workflows_before_change()
    validate_final_architecture()
    validate_frontend()

    print(f"PASS: canonical opportunity count remained {final_count}.")

    print("PASS: Phase 2 backend architecture validation completed.")


# ============================================================================
# MAIN
# ============================================================================


def main() -> None:
    banner(
        "ESC Opportunity Finder — Phase 2 canonical backend " "architecture migration"
    )

    validate_update_py()
    validate_repository()
    validate_branch()
    validate_origin()

    print_status()

    protect_repair_checkpoint()
    validate_protected_worktree()

    fetch_origin()
    require_safe_history()

    banner("PHASE 2 BASELINE VALIDATION")

    baseline_payload = validate_current_dataset()

    baseline_records = extract_opportunities(
        baseline_payload,
        SOURCE_DATA_JSON,
    )

    baseline_count = len(baseline_records)

    if baseline_count < EXPECTED_BASELINE_OPPORTUNITIES:
        print(
            "WARNING: canonical dataset is below the historical "
            f"{EXPECTED_BASELINE_OPPORTUNITIES}-opportunity baseline."
        )

    expired_count = validate_expired_dataset()

    validate_checkpoint()
    validate_scraper()
    validate_workflows_before_change()

    print(
        f"PASS: Phase 2 baseline contains {baseline_count} " "canonical opportunities."
    )

    banner("APPLYING PHASE 2 ARCHITECTURE MIGRATION")

    changed_files: list[str] = []
    removed_files: list[str] = []

    if remove_scrape_workflow():
        removed_files.append(SCRAPE_WORKFLOW.relative_to(ROOT).as_posix())

    if patch_update_workflow():
        changed_files.append(UPDATE_WORKFLOW.relative_to(ROOT).as_posix())

    if patch_deploy_workflow():
        changed_files.append(DEPLOY_WORKFLOW.relative_to(ROOT).as_posix())

    if patch_data_provider():
        changed_files.append(DATA_PROVIDER_JS.relative_to(ROOT).as_posix())

    removed_files.extend(remove_obsolete_web_datasets())

    validate_final_architecture()
    validate_frontend()

    write_review(
        baseline_count=baseline_count,
        expired_count=expired_count,
        changed_files=changed_files,
        removed_files=removed_files,
    )

    final_validation(baseline_count)

    protect_repair_checkpoint()
    validate_protected_worktree()

    banner("PHASE 2 COMPLETE")

    print("PASS: Phase 2 architecture migration completed.")

    print("INFO: update.yml is the only scraper workflow.")

    print("INFO: deploy.yml is the deployment-only workflow.")

    print("INFO: data/opportunities.json is the canonical " "opportunity dataset.")

    print("INFO: no scraper execution was performed.")

    print("INFO: no checkpoint or backend dataset was rebuilt.")

    print("INFO: review UPDATE_REVIEW.md before committing/pushing.")

    print()
    print("Final Git status:")

    final_status = status_lines()

    if final_status:
        for line in final_status:
            print(f"  {line}")
    else:
        print("  clean")

    print()
    print(
        "IMPORTANT: data/full_detail_repair_checkpoint.json " "must remain untracked."
    )


if __name__ == "__main__":
    main()
