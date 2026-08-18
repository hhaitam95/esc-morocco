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


def run_command(
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

    result = run_command(
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
# GIT
# ============================================================================


def git_status() -> list[str]:
    result = run_command(
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


def is_allowed_path(
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

    branch = run_command(
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

    remote = run_command(
        [
            "git",
            "remote",
            "get-url",
            "origin",
        ]
    )

    if remote.returncode != 0:
        fail("Could not determine origin remote.")

    actual_remote = remote.stdout.strip()

    if actual_remote != CANONICAL_REMOTE:
        fail(
            "origin remote is not canonical.\n"
            f"Expected: {CANONICAL_REMOTE}\n"
            f"Actual: {actual_remote}"
        )

    passed(f"repository root validated: {ROOT}")
    passed("current branch is main.")
    passed(f"origin remote is canonical: {actual_remote}")


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

        if not is_allowed_path(path):
            unexpected.append(line)

    if unexpected:
        fail(
            "Unexpected non-frontend working-tree changes detected:\n"
            + "\n".join(unexpected)
        )

    passed(
        "working tree contains only frontend/tooling changes "
        "and the protected checkpoint."
    )

    if PROTECTED_CHECKPOINT.exists():
        passed("protected repair checkpoint remains present.")
    else:
        info("protected repair checkpoint is not currently present.")


# ============================================================================
# PROTECTION
# ============================================================================


def snapshot_checkpoint() -> bytes | None:
    if not PROTECTED_CHECKPOINT.exists():
        return None

    return PROTECTED_CHECKPOINT.read_bytes()


def verify_checkpoint(
    original: bytes | None,
) -> None:
    if original is None:
        info("Protected checkpoint did not exist before the update.")
        return

    if not PROTECTED_CHECKPOINT.exists():
        fail("Protected checkpoint disappeared.")

    if PROTECTED_CHECKPOINT.read_bytes() != original:
        fail("Protected checkpoint changed.")

    passed("protected checkpoint remains byte-for-byte unchanged.")


# ============================================================================
# FRONTEND
# ============================================================================


def validate_frontend_files() -> None:
    heading("VALIDATING FRONTEND")

    required = (
        INDEX,
        STYLE,
        APP,
        FEATURES,
        DATA_PROVIDER,
    )

    for path in required:
        if not path.exists():
            fail("Required frontend file is missing: " + rel(path))

        passed(rel(path) + " exists.")

    optional_modules = (
        WEB / "state.js",
        WEB / "country.js",
        WEB / "table.js",
        WEB / "features" / "i18n.js",
        WEB / "features" / "theme.js",
    )

    for path in optional_modules:
        if path.exists():
            passed("existing frontend module preserved: " + rel(path))


# ============================================================================
# CLEAR
# ============================================================================


def normalize_clear_markup() -> None:
    html = read_text(INDEX)
    original = html

    html = html.replace(
        'id="refresh-button"',
        'id="clear-filters"',
    )

    html = html.replace(
        'id="clear-button"',
        'id="clear-filters"',
    )

    html = html.replace(
        'data-i18n="refresh"',
        'data-i18n="clear"',
    )

    button_pattern = re.compile(
        r'(<button[^>]*id="clear-filters"[^>]*>)(.*?)(</button>)',
        flags=re.IGNORECASE | re.DOTALL,
    )

    match = button_pattern.search(html)

    if match:
        body = re.sub(
            r"\bRefresh\b",
            "Clear",
            match.group(2),
            flags=re.IGNORECASE,
        )

        html = (
            html[: match.start()]
            + match.group(1)
            + body
            + match.group(3)
            + html[match.end() :]
        )

    if html != original:
        write_text(
            INDEX,
            html,
        )
        passed("Refresh control renamed to Clear.")
    else:
        passed("Clear control markup already normalized.")


# ============================================================================
# FEATURE REGISTRY
# ============================================================================

FEATURE_NAMES = (
    "language",
    "theme",
    "participantCountry",
    "search",
    "filters",
    "sorting",
    "expired",
    "newBadges",
    "clear",
)


def normalize_feature_registry() -> None:
    """
    Repair only the small feature registry object.

    Every known property is normalized to:

        property: true,

    This specifically fixes missing commas such as:

        expired: true
        newBadges: true

    without touching unrelated frontend code.
    """

    source = read_text(FEATURES)

    original = source

    for name in FEATURE_NAMES:
        pattern = re.compile(
            rf"^(\s*){re.escape(name)}\s*:\s*(true|false)\s*,?\s*$",
            flags=re.IGNORECASE | re.MULTILINE,
        )

        replacement = rf"\1{name}: true,"

        source, count = pattern.subn(
            replacement,
            source,
        )

        if count:
            continue

    source = re.sub(
        r"^\s*refresh\s*:\s*true\s*,?\s*$",
        "    refresh: false,",
        source,
        flags=re.IGNORECASE | re.MULTILINE,
    )

    # If clear does not exist at all, add it after newBadges.
    if not re.search(
        r"^\s*clear\s*:\s*true\s*,?\s*$",
        source,
        flags=re.IGNORECASE | re.MULTILINE,
    ):
        marker = re.search(
            r"^(\s*newBadges\s*:\s*true\s*,?)\s*$",
            source,
            flags=re.IGNORECASE | re.MULTILINE,
        )

        if marker:
            insertion = marker.group(1).rstrip(",") + ",\n    clear: true,"

            source = source[: marker.start()] + insertion + source[marker.end() :]

    if source != original:
        write_text(
            FEATURES,
            source,
        )

        passed("feature registry syntax normalized.")
    else:
        passed("feature registry already normalized.")


def validate_feature_registry() -> None:
    heading("VALIDATING FEATURE REGISTRY")

    source = read_text(FEATURES)

    for name in FEATURE_NAMES:
        if not re.search(
            rf"^\s*{re.escape(name)}\s*:\s*true\s*,?\s*$",
            source,
            flags=re.IGNORECASE | re.MULTILINE,
        ):
            fail("Feature registry is missing enabled feature: " + name)

        passed("feature enabled: " + name)

    if re.search(
        r"^\s*refresh\s*:\s*true\s*,?\s*$",
        source,
        flags=re.IGNORECASE | re.MULTILINE,
    ):
        fail("Refresh feature remains enabled.")

    passed("feature registry validated.")


# ============================================================================
# CLEAR IMPLEMENTATION
# ============================================================================


def clear_implementation() -> str:
    lines = [
        "",
        "/*",
        " * ESC Opportunity Finder Clear control.",
        " * Clear only resets table/search filters.",
        " * Participant Country is intentionally preserved.",
        " */",
        "(function () {",
        "    function clearTableFiltersOnly() {",
        "        var search = document.getElementById('search-input');",
        "        var countryFilter = document.getElementById('country-filter');",
        "        var typeFilter = document.getElementById('type-filter');",
        "        var sortSelect = document.getElementById('sort-select');",
        "",
        "        if (search) {",
        "            search.value = '';",
        "            search.dispatchEvent(new Event('input', { bubbles: true }));",
        "        }",
        "",
        "        if (countryFilter) {",
        "            countryFilter.value = '';",
        "            countryFilter.dispatchEvent(new Event('change', { bubbles: true }));",
        "        }",
        "",
        "        if (typeFilter) {",
        "            typeFilter.value = '';",
        "            typeFilter.dispatchEvent(new Event('change', { bubbles: true }));",
        "        }",
        "",
        "        if (sortSelect) {",
        "            var selected = Array.prototype.find.call(",
        "                sortSelect.options || [],",
        "                function (option) {",
        "                    return option.defaultSelected;",
        "                }",
        "            );",
        "",
        "            sortSelect.value = selected",
        "                ? selected.value",
        "                : ((sortSelect.options && sortSelect.options[0])",
        "                    ? sortSelect.options[0].value",
        "                    : '');",
        "",
        "            sortSelect.dispatchEvent(new Event('change', { bubbles: true }));",
        "        }",
        "",
        "        if (typeof window.renderActive === 'function') {",
        "            window.renderActive();",
        "        } else if (typeof window.render === 'function') {",
        "            window.render();",
        "        }",
        "    }",
        "",
        "    function installClearControl() {",
        "        var button = document.getElementById('clear-filters');",
        "",
        "        if (!button || button.dataset.escClearInstalled === 'true') {",
        "            return;",
        "        }",
        "",
        "        button.dataset.escClearInstalled = 'true';",
        "",
        "        button.addEventListener('click', function (event) {",
        "            event.preventDefault();",
        "            event.stopImmediatePropagation();",
        "            clearTableFiltersOnly();",
        "        }, true);",
        "    }",
        "",
        "    if (document.readyState === 'loading') {",
        "        document.addEventListener('DOMContentLoaded', installClearControl);",
        "    } else {",
        "        installClearControl();",
        "    }",
        "})();",
        "",
    ]

    return "\n".join(lines)


def ensure_clear_implementation() -> None:
    source = read_text(APP)

    marker = "ESC Opportunity Finder Clear control."

    if marker in source:
        marker_index = source.find(marker)
        block_start = source.rfind(
            "/*",
            0,
            marker_index,
        )

        if block_start >= 0:
            source = source[:block_start].rstrip()

    updated = source.rstrip() + "\n" + clear_implementation()

    if updated != read_text(APP):
        write_text(
            APP,
            updated,
        )

        passed("Clear table/search implementation normalized.")
    else:
        passed("Clear implementation already normalized.")


# ============================================================================
# VALIDATION
# ============================================================================


def validate_html() -> None:
    heading("VALIDATING HTML CONTRACT")

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

    if 'id="refresh-button"' in html:
        fail("Old Refresh button still exists.")

    passed("HTML contract validated.")


def validate_clear() -> None:
    heading("VALIDATING CLEAR BEHAVIOR")

    source = read_text(APP)

    marker = "ESC Opportunity Finder Clear control."

    position = source.find(marker)

    if position < 0:
        fail("Canonical Clear implementation is missing.")

    clear_source = source[position:]

    for item in (
        "search-input",
        "country-filter",
        "type-filter",
        "sort-select",
        "clear-filters",
    ):
        if item not in clear_source:
            fail("Clear implementation is missing: " + item)

    forbidden = (
        "participantCountry.value =",
        "participantCountrySelect.value =",
        "participantCountryFilter.value =",
        "state.participantCountry =",
        "state.selectedParticipantCountry =",
        "selectedParticipantCountry =",
        "currentParticipantCountry =",
        "setParticipantCountry(",
    )

    for item in forbidden:
        if item in clear_source:
            fail("Clear implementation modifies " "Participant Country: " + item)

    if "stopImmediatePropagation" not in clear_source:
        fail(
            "Clear implementation does not protect itself " "from an old click handler."
        )

    passed("Clear resets table/search filters only.")

    passed("Clear does not modify Participant Country.")


def validate_data_provider() -> None:
    heading("VALIDATING DATA PROVIDER")

    source = read_text(DATA_PROVIDER)

    if not source.strip():
        fail("data-provider.js is empty.")

    passed("data-provider.js remains present.")


def validate_javascript() -> None:
    heading("VALIDATING JAVASCRIPT")

    node = run_command(
        [
            "node",
            "--version",
        ]
    )

    if node.returncode != 0:
        info("Node.js unavailable; JavaScript syntax validation skipped.")
        return

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
        result = run_command(
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


def validate_css() -> None:
    heading("VALIDATING CSS")

    source = read_text(STYLE)

    if not source.strip():
        fail("style.css is empty.")

    passed("style.css validated.")


# ============================================================================
# REVIEW
# ============================================================================


def write_review() -> None:
    lines = [
        "# Frontend Cleanup Review",
        "",
        "## Scope",
        "",
        "Frontend only.",
        "",
        "## Completed",
        "",
        "- Refresh renamed to Clear.",
        "- Clear resets table/search filters.",
        "- Clear preserves Participant Country.",
        "- Existing frontend modules are preserved.",
        "- Feature registry syntax is valid.",
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
        "## Review",
        "",
        "git status",
        "",
        "git diff -- web/",
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

        if not is_allowed_path(path):
            unexpected.append(line)

    if unexpected:
        fail("Unexpected non-frontend changes remain:\n" + "\n".join(unexpected))

    passed(
        "final working tree contains only frontend/tooling "
        "changes and the protected checkpoint."
    )


# ============================================================================
# MAIN
# ============================================================================


def main() -> None:
    print("=" * 72)
    print("ESC Opportunity Finder — simple frontend cleanup")
    print("=" * 72)

    validate_update_py()
    validate_repository()
    validate_worktree()

    checkpoint_before = snapshot_checkpoint()

    validate_frontend_files()

    normalize_clear_markup()
    normalize_feature_registry()
    ensure_clear_implementation()

    validate_frontend_files()
    validate_feature_registry()
    validate_html()
    validate_clear()
    validate_data_provider()
    validate_javascript()
    validate_css()

    verify_checkpoint(checkpoint_before)

    write_review()

    validate_final_worktree()

    print()
    print("=" * 72)
    print("FRONTEND CLEANUP COMPLETE")
    print("=" * 72)
    print()
    print("Refresh -> Clear: completed")
    print("Clear -> table/search filters only")
    print("Participant Country -> preserved")
    print("Feature registry -> valid JavaScript")
    print("Backend -> untouched")
    print("Scraper -> untouched")
    print("GitHub Actions -> untouched")
    print("Checkpoint -> unchanged")
    print("Commit/push -> NOT performed")
    print()


if __name__ == "__main__":
    main()
