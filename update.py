#!/usr/bin/env python3

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"

INDEX = WEB / "index.html"
APP = WEB / "app.js"
FEATURES = WEB / "features.js"
DATA_PROVIDER = WEB / "data-provider.js"
STYLE = WEB / "style.css"

REVIEW = ROOT / "UPDATE_REVIEW.md"
PROTECTED_CHECKPOINT = ROOT / "data" / "full_detail_repair_checkpoint.json"

CANONICAL_REMOTE = "https://github.com/hhaitam95/esc-opportunity-finder.git"


# ============================================================================
# OUTPUT
# ============================================================================


def heading(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def passed(message: str) -> None:
    print(f"PASS: {message}")


def info(message: str) -> None:
    print(f"INFO: {message}")


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    print("No destructive cleanup was performed.")
    raise SystemExit(1)


# ============================================================================
# HELPERS
# ============================================================================


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def read_text(path: Path) -> str:
    if not path.exists():
        fail(f"Required file is missing: {rel(path)}")

    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        fail(f"Could not read {rel(path)}: {exc}")

    return ""


def write_text(
    path: Path,
    content: str,
) -> None:
    try:
        path.write_text(
            content,
            encoding="utf-8",
        )
    except Exception as exc:
        fail(f"Could not write {rel(path)}: {exc}")


def run(
    args: list[str],
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(
            args,
            127,
            f"Command not found: {args[0]}",
        )


# ============================================================================
# SELF VALIDATION
# ============================================================================


def validate_update_py() -> None:
    source = Path(__file__).read_text(encoding="utf-8")

    try:
        ast.parse(source)
    except SyntaxError as exc:
        fail("update.py AST validation failed:\n" f"line {exc.lineno}: {exc.msg}")

    result = run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(Path(__file__).resolve()),
        ]
    )

    if result.returncode != 0:
        fail("update.py py_compile validation failed:\n" + result.stdout)

    passed("update.py syntax validated.")


# ============================================================================
# REPOSITORY
# ============================================================================


def git_status() -> list[str]:
    result = run(
        [
            "git",
            "status",
            "--porcelain=v1",
        ]
    )

    if result.returncode != 0:
        fail("Unable to read Git status:\n" + result.stdout)

    return [line for line in result.stdout.splitlines() if line.strip()]


def status_path(
    line: str,
) -> str | None:
    if len(line) < 4:
        return None

    value = line[3:].strip()

    if " -> " in value:
        value = value.split(
            " -> ",
            1,
        )[1]

    return value


def allowed_path(
    path: str,
) -> bool:
    if path.startswith("web/"):
        return True

    return path in {
        "update.py",
        "UPDATE_REVIEW.md",
        "data/full_detail_repair_checkpoint.json",
    }


def validate_repository() -> None:
    heading("VALIDATING REPOSITORY")

    if not (ROOT / ".git").exists():
        fail("Current directory is not a Git repository.")

    branch = run(
        [
            "git",
            "branch",
            "--show-current",
        ]
    )

    if branch.returncode != 0:
        fail("Could not determine current branch.")

    if branch.stdout.strip() != "main":
        fail("Expected branch main, found " f"{branch.stdout.strip()!r}")

    remote = run(
        [
            "git",
            "remote",
            "get-url",
            "origin",
        ]
    )

    if remote.returncode != 0:
        fail("Could not determine origin remote.")

    actual = remote.stdout.strip()

    if actual != CANONICAL_REMOTE:
        fail(
            "origin remote is not canonical.\n"
            f"Expected: {CANONICAL_REMOTE}\n"
            f"Actual: {actual}"
        )

    passed(f"repository root validated: {ROOT}")
    passed("current branch is main.")
    passed(f"origin remote is canonical: {actual}")


def validate_worktree() -> None:
    heading("VALIDATING WORKING TREE")

    status = git_status()

    print("Current Git status:")

    if status:
        for line in status:
            print(line)
    else:
        print(" clean")

    unexpected: list[str] = []

    for line in status:
        path = status_path(line)

        if path is None:
            unexpected.append(line)
            continue

        if not allowed_path(path):
            unexpected.append(line)

    if unexpected:
        fail("Unexpected non-frontend changes detected:\n" + "\n".join(unexpected))

    passed(
        "working tree contains only frontend/tooling changes "
        "and the protected checkpoint."
    )

    if PROTECTED_CHECKPOINT.exists():
        passed("protected repair checkpoint remains present.")
    else:
        info("protected repair checkpoint is not currently present.")


# ============================================================================
# CHECKPOINT
# ============================================================================


def snapshot_checkpoint() -> bytes | None:
    if not PROTECTED_CHECKPOINT.exists():
        return None

    return PROTECTED_CHECKPOINT.read_bytes()


def verify_checkpoint(
    original: bytes | None,
) -> None:

    if original is None:
        info("Protected checkpoint did not exist before update.")
        return

    if not PROTECTED_CHECKPOINT.exists():
        fail("Protected checkpoint disappeared.")

    if PROTECTED_CHECKPOINT.read_bytes() != original:
        fail("Protected checkpoint was modified.")

    passed("protected checkpoint remains byte-for-byte unchanged.")


# ============================================================================
# FRONTEND
# ============================================================================


def validate_frontend_files() -> None:
    heading("VALIDATING FRONTEND FILES")

    for path in (
        INDEX,
        APP,
        FEATURES,
        DATA_PROVIDER,
        STYLE,
    ):
        if not path.exists():
            fail(f"Missing frontend file: {rel(path)}")

        passed(rel(path) + " exists.")

    for path in (
        WEB / "state.js",
        WEB / "country.js",
        WEB / "table.js",
        WEB / "features" / "i18n.js",
        WEB / "features" / "theme.js",
    ):
        if path.exists():
            passed("existing frontend module preserved: " + rel(path))


# ============================================================================
# APP.JS REPAIR
# ============================================================================


def repair_app_js() -> bool:
    source = read_text(APP)

    original = source

    source = re.sub(
        r"(?m)^[ \t]*dom\.[ \t]*$\n?",
        "",
        source,
    )

    if source == original:
        passed("app.js contains no stray standalone dom. lines.")
        return False

    write_text(
        APP,
        source,
    )

    passed("removed malformed standalone dom. lines from app.js.")

    return True


# ============================================================================
# FEATURE REGISTRY
# ============================================================================


def repair_features_js() -> bool:
    """
    Repair comma-separated boolean properties without rebuilding the module.

    The common corruption is:

        expired: true
        newBadges: true

    which must become:

        expired: true,
        newBadges: true,
    """

    source = read_text(FEATURES)
    original = source

    feature_names = (
        "language",
        "theme",
        "participantCountry",
        "search",
        "filters",
        "sorting",
        "expired",
        "newBadges",
        "clear",
        "archives",
    )

    for index, name in enumerate(feature_names):
        if index == len(feature_names) - 1:
            continue

        next_name = feature_names[index + 1]

        pattern = re.compile(
            rf"(^[ \t]*{re.escape(name)}[ \t]*:[ \t]*(?:true|false))"
            rf"[ \t]*\n"
            rf"(?=[ \t]*{re.escape(next_name)}[ \t]*:)",
            re.MULTILINE,
        )

        source = pattern.sub(
            lambda match: match.group(1) + ",\n",
            source,
        )

    # The last registry property must not accidentally be missing its comma
    # if another property follows immediately afterward.
    source = re.sub(
        r"(^[ \t]*clear[ \t]*:[ \t]*(?:true|false))"
        r"[ \t]*\n"
        r"(?=[ \t]*archives[ \t]*:)",
        r"\1,\n",
        source,
        flags=re.MULTILINE,
    )

    if source != original:
        write_text(
            FEATURES,
            source,
        )

        passed("features.js registry comma formatting repaired.")
        return True

    passed("features.js registry formatting already normalized.")
    return False


# ============================================================================
# CLEAR
# ============================================================================


def validate_clear() -> None:
    heading("VALIDATING CLEAR")

    html = read_text(INDEX)
    app = read_text(APP)

    if 'id="clear-filters"' not in html:
        fail("Clear control is missing.")

    if 'id="refresh-button"' in html:
        fail("Old Refresh control remains.")

    if "clearFilters" not in app:
        fail("app.js does not contain clearFilters().")

    start = app.find("function clearFilters")

    if start < 0:
        fail("Could not locate clearFilters().")

    end = app.find(
        "function bindEvents",
        start,
    )

    if end < 0:
        end = len(app)

    clear_source = app[start:end]

    required = (
        "clearTableFilters",
        "searchInput",
        "countryFilter",
        "typeFilter",
        "sortSelect",
    )

    for marker in required:
        if marker not in clear_source:
            fail("clearFilters() is missing: " + marker)

    if "setParticipantCountry(" in clear_source:
        fail("Clear incorrectly modifies Participant Country.")

    passed("Clear resets table/search filters only.")

    passed("Clear preserves Participant Country.")


# ============================================================================
# HTML
# ============================================================================


def validate_html() -> None:
    heading("VALIDATING HTML")

    html = read_text(INDEX)

    for element_id in (
        "participant-country",
        "clear-filters",
        "search-input",
        "country-filter",
        "type-filter",
        "sort-select",
    ):
        if f'id="{element_id}"' not in html:
            fail("Missing HTML element: " + element_id)

    passed("HTML contract validated.")


# ============================================================================
# DATA PROVIDER
# ============================================================================


def validate_data_provider() -> None:
    heading("VALIDATING DATA PROVIDER")

    source = read_text(DATA_PROVIDER)

    if not source.strip():
        fail("data-provider.js is empty.")

    passed("data-provider.js remains present.")


# ============================================================================
# JAVASCRIPT
# ============================================================================


def validate_javascript() -> None:
    heading("VALIDATING JAVASCRIPT")

    node = run(
        [
            "node",
            "--version",
        ]
    )

    if node.returncode != 0:
        fail("Node.js is required for frontend validation.")

    passed("Node.js available: " + node.stdout.strip())

    files = [
        APP,
        FEATURES,
        DATA_PROVIDER,
    ]

    for path in (
        WEB / "state.js",
        WEB / "country.js",
        WEB / "table.js",
        WEB / "features" / "i18n.js",
        WEB / "features" / "theme.js",
    ):
        if path.exists():
            files.append(path)

    for path in files:
        result = run(
            [
                "node",
                "--check",
                str(path),
            ]
        )

        if result.returncode != 0:
            fail(
                "JavaScript syntax validation failed for "
                + rel(path)
                + ":\n"
                + result.stdout
            )

        passed(rel(path) + " syntax validated.")


# ============================================================================
# CSS
# ============================================================================


def validate_css() -> None:
    source = read_text(STYLE)

    if not source.strip():
        fail("style.css is empty.")

    passed("style.css validated.")


# ============================================================================
# REVIEW
# ============================================================================


def write_review() -> None:
    lines = [
        "# Frontend Production Fix",
        "",
        "## Changes",
        "",
        "- repaired malformed standalone `dom.` lines in `web/app.js`;",
        "- repaired `web/features.js` comma formatting;",
        "- preserved Clear behavior;",
        "- preserved Participant Country;",
        "",
        "## Protected",
        "",
        "- scraper/",
        "- data/",
        "- .github/",
        "- deployment configuration",
        "- protected repair checkpoint",
        "",
        "No commit or push was performed.",
        "",
    ]

    write_text(
        REVIEW,
        "\n".join(lines),
    )

    passed("UPDATE_REVIEW.md generated.")


# ============================================================================
# FINAL
# ============================================================================


def validate_final_worktree() -> None:
    heading("FINAL VALIDATION")

    status = git_status()

    if status:
        for line in status:
            print(line)
    else:
        print(" clean")

    unexpected: list[str] = []

    for line in status:
        path = status_path(line)

        if path is None:
            unexpected.append(line)
            continue

        if not allowed_path(path):
            unexpected.append(line)

    if unexpected:
        fail("Unexpected changes remain:\n" + "\n".join(unexpected))

    passed(
        "final working tree contains only frontend/tooling "
        "changes and the protected checkpoint."
    )


# ============================================================================
# MAIN
# ============================================================================


def main() -> None:
    print("=" * 72)
    print("ESC Opportunity Finder — frontend production fix")
    print("=" * 72)

    validate_update_py()
    validate_repository()
    validate_worktree()

    checkpoint_before = snapshot_checkpoint()

    validate_frontend_files()

    repair_app_js()
    repair_features_js()

    validate_frontend_files()
    validate_clear()
    validate_html()
    validate_data_provider()
    validate_javascript()
    validate_css()

    verify_checkpoint(checkpoint_before)

    write_review()

    validate_final_worktree()

    print()
    print("=" * 72)
    print("FRONTEND PRODUCTION FIX COMPLETE")
    print("=" * 72)
    print()
    print("app.js: repaired")
    print("features.js: repaired")
    print("Clear: preserved")
    print("Participant Country: preserved")
    print("Backend: untouched")
    print("Scraper: untouched")
    print("GitHub Actions: untouched")
    print("Checkpoint: unchanged")
    print("Commit/push: NOT performed")
    print()


if __name__ == "__main__":
    main()
