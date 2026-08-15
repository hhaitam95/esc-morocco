#!/usr/bin/env python3

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
APP_JS = ROOT / "web" / "app.js"
INDEX_HTML = ROOT / "web" / "index.html"


def run(command, check=True):
    print(f"$ {' '.join(command)}")

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
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}: "
            f"{' '.join(command)}"
        )

    return result


def fail(message):
    print()
    print("=" * 72)
    print("UPDATE FAILED")
    print("=" * 72)
    print()
    print(message)
    print()
    print("No commit or push was performed.")
    sys.exit(1)


def main():
    print("=" * 72)
    print("ESC Opportunity Finder — neutral results/status reset fix")
    print("=" * 72)
    print()

    # ------------------------------------------------------------
    # FILES
    # ------------------------------------------------------------

    print("Checking required files...")

    for path in (
        APP_JS,
        INDEX_HTML,
        ROOT / "scraper" / "scraper.py",
    ):
        if not path.exists():
            fail(f"Required file does not exist: {path}")

    print("PASS: required files exist.")
    print()

    # ------------------------------------------------------------
    # GIT
    # ------------------------------------------------------------

    print("Checking Git state...")
    status = run(["git", "status", "--short"])

    if status.stdout.strip():
        print("Working tree:")
        print(status.stdout.rstrip())
    else:
        print("Working tree is clean.")

    print()
    print("NOTE: Existing web/app.js changes will be repaired in place.")
    print()

    print("Checking branch...")
    branch = run(["git", "branch", "--show-current"]).stdout.strip()

    if branch != "main":
        fail(f"Current branch is {branch!r}; expected main.")

    print("PASS: current branch is main.")
    print()

    print("Checking remote safety...")
    run(["git", "fetch", "origin", "main"])

    sync = (
        run(["git", "rev-list", "--left-right", "--count", "main...origin/main"])
        .stdout.strip()
        .split()
    )

    if len(sync) != 2:
        fail("Could not determine Git synchronization state.")

    local_only = int(sync[0])
    remote_only = int(sync[1])

    print(f"Local-only commits: {local_only}")
    print(f"Remote-only commits: {remote_only}")

    if local_only != 0 or remote_only != 0:
        fail("Local main is not synchronized with origin/main.")

    print("PASS: local main is synchronized with origin/main.")
    print()

    # ------------------------------------------------------------
    # LOAD FILES
    # ------------------------------------------------------------

    app = APP_JS.read_text(encoding="utf-8")
    html = INDEX_HTML.read_text(encoding="utf-8")

    print("Loaded current local web/app.js.")
    print()

    # ------------------------------------------------------------
    # PARTICIPANT COUNTRY
    # ------------------------------------------------------------

    print("Validating participant-country architecture...")

    if "participant-country" not in app:
        fail("Participant-country logic is missing from web/app.js.")

    if "participant-country" not in html:
        fail("Participant-country markup is missing from web/index.html.")

    if 'id="participant-country"' not in html:
        fail("Participant-country selector is missing from web/index.html.")

    if 'id="apply-participant-country"' not in html:
        fail("Participant-country Search button is missing from " "web/index.html.")

    if "selectedParticipantCountry" not in app:
        fail("selectedParticipantCountry state is missing.")

    if "participantSearchApplied" not in app:
        fail("participantSearchApplied state is missing.")

    if "function applyParticipantCountry()" not in app:
        fail("applyParticipantCountry() is missing.")

    if '"Morocco"' not in app or "🇲🇦" not in app:
        fail("Morocco participant-country is missing.")

    print("PASS: participant-country architecture is present.")
    print("PASS: Morocco participant-country remains present.")
    print()

    # ------------------------------------------------------------
    # TRANSLATIONS
    # ------------------------------------------------------------

    print("Validating Search translations...")

    for language, value in (
        ("EN", "Search"),
        ("FR", "Rechercher"),
        ("AR", "بحث"),
    ):
        if value not in app:
            fail(f"Missing {language} Search translation: {value!r}")

    print("PASS: EN / FR / AR use Search.")
    print()

    # ------------------------------------------------------------
    # REPAIR renderActive()
    # ------------------------------------------------------------

    print("Repairing renderActive()...")

    render_pattern = re.compile(
        r"function\s+renderActive\(\)"
        r"\s*(?:\{)?"
        r"\s*if\s*\(!participantSearchApplied\)\s*\{"
        r"\s*resetParticipantSearchDisplay\(\);"
        r"\s*return;"
        r"\s*\}",
        re.DOTALL,
    )

    render_match = render_pattern.search(app)

    if not render_match:
        fail("Could not locate the current renderActive() neutral-state " "guard.")

    render_replacement = """function renderActive() {
  if (!participantSearchApplied) {
    resetParticipantSearchDisplay();
    return;
  }"""

    app = app[: render_match.start()] + render_replacement + app[render_match.end() :]

    print("PASS: renderActive() repaired.")
    print()

    # ------------------------------------------------------------
    # REPAIR updateHeader()
    # ------------------------------------------------------------

    print("Repairing updateHeader()...")

    header_pattern = re.compile(
        r"function\s+updateHeader\(data\)"
        r"\s*(?:\{)?"
        r"\s*if\s*\(!participantSearchApplied\)\s*\{"
        r"\s*resetParticipantSearchDisplay\(\);"
        r"\s*return;"
        r"\s*\}",
        re.DOTALL,
    )

    header_match = header_pattern.search(app)

    if not header_match:
        fail("Could not locate the current updateHeader() neutral-state " "guard.")

    header_replacement = """function updateHeader(data) {
  if (!participantSearchApplied) {
    resetParticipantSearchDisplay();
    return;
  }"""

    app = app[: header_match.start()] + header_replacement + app[header_match.end() :]

    print("PASS: updateHeader() repaired.")
    print()

    # ------------------------------------------------------------
    # RESET HELPER
    # ------------------------------------------------------------

    print("Validating neutral reset helper...")

    if "function resetParticipantSearchDisplay()" not in app:
        fail("resetParticipantSearchDisplay() is missing.")

    reset_start = app.index("function resetParticipantSearchDisplay()")

    next_function = re.search(
        r"\nfunction\s+\w+\s*\(",
        app[reset_start + 1 :],
    )

    if next_function:
        reset_end = reset_start + 1 + next_function.start()
        reset_block = app[reset_start:reset_end]
    else:
        reset_block = app[reset_start:]

    for value in (
        'opportunityCount.textContent = "—";',
        'activeResultCount.textContent = "—";',
        'lastUpdated.textContent = "—";',
        'opportunitiesBody.innerHTML = "";',
    ):
        if value not in reset_block:
            fail("Neutral reset helper is missing required operation: " f"{value}")

    print("PASS: neutral reset helper is correct.")
    print()

    # ------------------------------------------------------------
    # SEARCH STATE
    # ------------------------------------------------------------

    print("Validating Search state behavior...")

    if "participantSearchApplied = Boolean(" not in app:
        fail("Search does not activate participantSearchApplied.")

    if "if (participantSearchApplied)" not in app:
        fail("Search activation branch is missing.")

    print("PASS: Search activation is present.")
    print()

    # ------------------------------------------------------------
    # LOAD DATA
    # ------------------------------------------------------------

    print("Validating initial load behavior...")

    load_match = re.search(
        r"async\s+function\s+loadData\(\)\s*\{",
        app,
    )

    if not load_match:
        fail("loadData() is missing.")

    refresh_marker = re.search(
        r"\n// ============================================================\n"
        r"// REFRESH BUTTON",
        app[load_match.start() :],
    )

    if not refresh_marker:
        fail("Could not determine loadData() boundaries.")

    load_block = app[load_match.start() : load_match.start() + refresh_marker.start()]

    if "resetParticipantSearchDisplay();" not in load_block:
        fail(
            "loadData() does not reset the active table/status cards " "before Search."
        )

    print("PASS: loadData() resets the active results.")
    print()

    # ------------------------------------------------------------
    # WRITE
    # ------------------------------------------------------------

    print("Writing repaired web/app.js...")
    APP_JS.write_text(app, encoding="utf-8")
    print("PASS: web/app.js updated.")
    print()

    # ------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------

    print("Running JavaScript syntax check...")
    result = run(["node", "--check", "web/app.js"], check=False)

    if result.returncode != 0:
        fail(
            "JavaScript syntax validation failed. "
            "web/app.js was not left in a validated state."
        )

    print("PASS: node --check web/app.js.")
    print()

    print("Running Git whitespace check...")
    run(["git", "diff", "--check"])
    print("PASS: git diff --check.")
    print()

    # ------------------------------------------------------------
    # DIFF
    # ------------------------------------------------------------

    print("Reviewing frontend diff...")
    run(["git", "diff", "--", "web/app.js"])

    print()
    print("=" * 72)
    print("UPDATE COMPLETE")
    print("=" * 72)
    print()
    print("Expected behavior:")
    print()
    print("  First visit / refresh:")
    print("    Participant Country: Select Participant Country")
    print("    Active opportunities: —")
    print("    Active result count: —")
    print("    Last updated: —")
    print("    Active table: empty")
    print()
    print("  Switching EN / FR / AR before Search:")
    print("    Active table remains empty")
    print("    Status cards remain —")
    print()
    print("  Selecting a participant country + Search:")
    print("    Participant-country filtering activates")
    print("    Active results render")
    print("    Status cards populate")
    print()
    print("No commit or push was performed.")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        fail(str(exc))
    except Exception as exc:
        fail(f"Unexpected error: {exc}")
