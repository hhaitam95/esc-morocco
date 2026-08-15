#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

WORKFLOW_PATH = ROOT / ".github" / "workflows" / "update.yml"

REQUIRED_FILES = [
    "scraper/scraper.py",
    "data/opportunities.json",
    "data/checkpoint.json",
    "data/expired.json",
    "web/opportunities.json",
]

MANAGED_FILES = [
    ".github/workflows/update.yml",
    "update.py",
]


BACKGROUND_WORKFLOW = """name: Update ESC Opportunities

on:
  # Run automatically every hour.
  # Offset from the top of the hour to reduce GitHub Actions scheduling
  # contention during high-load periods.
  schedule:
    - cron: "17 * * * *"

  # Allow manual runs from GitHub Actions.
  workflow_dispatch:

permissions:
  contents: write

# The scraper and checkpoint/cache files are repository state.
# Never allow two background scraper runs to modify them simultaneously.
concurrency:
  group: esc-opportunity-cache-writer
  cancel-in-progress: false

jobs:
  update-opportunities:
    runs-on: ubuntu-latest

    # A single invocation processes up to 40 detail pages.
    # Multiple invocations are used during one workflow run so the
    # incremental queue can make meaningful progress while remaining
    # bounded and resumable.
    timeout-minutes: 90

    steps:
      # ==============================================================
      # CHECKOUT
      # ==============================================================

      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      # ==============================================================
      # PYTHON
      # ==============================================================

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      # ==============================================================
      # DEPENDENCIES
      #
      # scraper.py currently requires:
      #   requests
      #   beautifulsoup4
      #   pycountry
      #
      # Keep installation explicit for now because the repository does
      # not currently have a dependency lock/requirements file.
      # ==============================================================

      - name: Install scraper dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install requests beautifulsoup4 pycountry

      # ==============================================================
      # GIT CONFIGURATION
      # ==============================================================

      - name: Configure Git
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

      # ==============================================================
      # VALIDATE SCRAPER BEFORE STARTING
      # ==============================================================

      - name: Validate scraper syntax
        run: |
          python -m py_compile scraper/scraper.py

      # ==============================================================
      # RUN INCREMENTAL SCRAPER BATCHES
      #
      # scraper.py itself is responsible for:
      #
      #   - retrieving the authoritative ESC opportunity list
      #   - loading checkpoint.json
      #   - building the incremental work queue
      #   - processing at most 40 detail pages
      #   - waiting between detail requests
      #   - retrying HTTP failures
      #   - stopping safely on HTTP 429
      #   - saving checkpoint progress after each opportunity
      #   - publishing the canonical JSON cache
      #
      # One invocation therefore remains deliberately small.
      #
      # Three invocations provide up to 120 detail-page scans per hourly
      # workflow while keeping the overall request volume bounded.
      #
      # Exit codes:
      #   0 = successful / normal incremental progress
      #   1 = genuine scraper failure
      #   2 = rate-limited or safely interrupted
      # ==============================================================

      - name: Run incremental scraper batches
        id: scraper
        continue-on-error: true
        run: |
          set +e

          MAX_BATCHES=3
          BATCH=1
          OVERALL_EXIT_CODE=0

          while [ "$BATCH" -le "$MAX_BATCHES" ]; do
            echo ""
            echo "================================================================"
            echo "ESC BACKGROUND SCRAPER — BATCH $BATCH / $MAX_BATCHES"
            echo "================================================================"
            echo ""

            python scraper/scraper.py
            EXIT_CODE=$?

            echo ""
            echo "Batch $BATCH exit code: $EXIT_CODE"
            echo ""

            # --------------------------------------------------------
            # Publish the latest canonical cache to the website.
            #
            # The scraper writes data/opportunities.json and
            # data/expired.json. The website consumes read-only copies.
            #
            # Never publish an empty or structurally invalid cache.
            # --------------------------------------------------------

            if [ -f data/opportunities.json ]; then
              python - <<'PY'
          import json
          from pathlib import Path

          path = Path("data/opportunities.json")
          data = json.loads(path.read_text(encoding="utf-8"))

          opportunities = data.get("opportunities")

          if not isinstance(opportunities, list):
              raise SystemExit(
                  "Canonical cache does not contain an opportunities list."
              )

          if not opportunities:
              raise SystemExit(
                  "Canonical cache is empty; refusing to publish it."
              )

          print(
              f"Validated canonical cache: {len(opportunities)} opportunities."
          )
          PY

              if [ $? -eq 0 ]; then
                cp data/opportunities.json web/opportunities.json
                echo "Published canonical opportunity cache to web/."
              else
                echo "Canonical cache validation failed; keeping published cache."
              fi
            fi

            if [ -f data/expired.json ]; then
              cp data/expired.json web/expired.json
            fi

            # --------------------------------------------------------
            # Commit only the files produced by the scraper.
            #
            # This protects unrelated repository changes.
            # --------------------------------------------------------

            git reset

            git add -- data/opportunities.json
            git add -- data/checkpoint.json
            git add -- data/expired.json
            git add -- web/opportunities.json
            git add -- web/expired.json

            STAGED="$(git diff --cached --name-only)"

            if [ -n "$STAGED" ]; then
              echo "Changes detected:"
              printf '%s\n' "$STAGED"

              git diff --cached --check
              if [ $? -ne 0 ]; then
                echo "Whitespace errors detected in staged cache changes."
                OVERALL_EXIT_CODE=1
                break
              fi

              git commit -m "chore: update ESC opportunity cache"

              if [ $? -ne 0 ]; then
                echo "Git commit failed."
                OVERALL_EXIT_CODE=1
                break
              fi

              git push origin main

              if [ $? -ne 0 ]; then
                echo "Git push failed."
                OVERALL_EXIT_CODE=1
                break
              fi

              echo "Cache changes committed and pushed."
            else
              echo "No cache changes after this batch."
            fi

            # --------------------------------------------------------
            # Genuine scraper failure.
            # --------------------------------------------------------

            if [ "$EXIT_CODE" -eq 1 ]; then
              echo ""
              echo "Genuine scraper failure detected."
              echo "Stopping the workflow."
              echo ""

              OVERALL_EXIT_CODE=1
              break
            fi

            # --------------------------------------------------------
            # Rate limiting is expected to be resumable.
            #
            # scraper.py saves its checkpoint before returning 2.
            # The completed progress has already been committed above.
            # Stop rather than increasing pressure on ESC.
            # --------------------------------------------------------

            if [ "$EXIT_CODE" -eq 2 ]; then
              echo ""
              echo "Rate limit or safe interruption detected."
              echo "Stopping remaining batches."
              echo "Checkpoint progress has been preserved."
              echo ""

              OVERALL_EXIT_CODE=2
              break
            fi

            BATCH=$((BATCH + 1))
          done

          echo "exit_code=$OVERALL_EXIT_CODE" >> "$GITHUB_OUTPUT"

          exit "$OVERALL_EXIT_CODE"

      # ==============================================================
      # FINAL STATUS
      # ==============================================================

      - name: Report scraper result
        if: always()
        run: |
          EXIT_CODE="${{ steps.scraper.outputs.exit_code }}"

          if [ "$EXIT_CODE" = "1" ]; then
            echo "ESC background scraper encountered a genuine failure."
            exit 1

          elif [ "$EXIT_CODE" = "2" ]; then
            echo "ESC background scraper stopped safely after rate limiting."
            echo "Saved checkpoint progress will be resumed by a future run."
            exit 0

          else
            echo "ESC background scraper completed normally."
            exit 0
          fi
"""


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
    return json.loads(read_text(path))


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


def git_status() -> str:
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
        print(
            "NOTE: This updater will stage only the explicitly managed "
            "background-workflow files."
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


def validate_scraper_architecture():
    print("\nValidating existing scraper architecture...")

    scraper = read_text(ROOT / "scraper/scraper.py")

    required_markers = [
        "API_URL",
        "CHECKPOINT_FILE",
        "OPPORTUNITIES_FILE",
        "BATCH_SIZE",
        "DETAIL_REQUEST_DELAY",
        "MAX_RETRIES",
        "fetch_current_opportunities",
        "load_checkpoint",
        "save_checkpoint",
        "build_work_queue",
        "fetch_detail_page",
        "save_public_output",
        "save_expired_output",
        "return 2",
    ]

    missing = [marker for marker in required_markers if marker not in scraper]

    if missing:
        raise RuntimeError(
            "Existing scraper architecture is missing required markers:\n"
            + "\n".join(f"  - {item}" for item in missing)
        )

    print(
        "PASS: existing incremental/resumable country-agnostic "
        "scraper architecture remains intact."
    )


def validate_scraper_is_country_agnostic():
    print("\nValidating country-agnostic background scraping...")

    scraper = read_text(ROOT / "scraper/scraper.py")

    if "filters[participant_country]" in scraper:
        raise RuntimeError(
            "Background scraper appears to filter the ESC API by "
            "participant country. Background discovery must remain global."
        )

    if "filters[eligible_country]" in scraper:
        raise RuntimeError(
            "Background scraper appears to filter the ESC API by "
            "eligible country. Background discovery must remain global."
        )

    if "DEFAULT_PARTICIPANT_COUNTRY" in scraper:
        print(
            "NOTE: scraper.py still contains its historical "
            "DEFAULT_PARTICIPANT_COUNTRY constant."
        )
        print(
            "PASS: no participant-country filter was detected in the "
            "background API query."
        )
    else:
        print(
            "PASS: scraper contains no participant-country-specific "
            "background configuration."
        )


def validate_existing_cache():
    print("\nValidating existing canonical cache...")

    data = load_json(ROOT / "data/opportunities.json")

    if not isinstance(data, dict):
        raise RuntimeError("data/opportunities.json must contain a JSON object.")

    opportunities = data.get("opportunities")

    if not isinstance(opportunities, list):
        raise RuntimeError("Canonical cache does not contain an opportunities list.")

    print(f"Current cached opportunities: {len(opportunities)}")

    if opportunities:
        with_country_data = sum(
            isinstance(item, dict)
            and isinstance(
                item.get("eligible_countries"),
                list,
            )
            for item in opportunities
        )

        print(
            "Opportunities containing participant-country data: " f"{with_country_data}"
        )

    print("PASS: canonical cache is structurally valid.")


def validate_workflow():
    print("\nValidating generated background workflow...")

    content = read_text(WORKFLOW_PATH)

    required_fragments = [
        "name: Update ESC Opportunities",
        "schedule:",
        'cron: "17 * * * *"',
        "workflow_dispatch:",
        "permissions:",
        "contents: write",
        "concurrency:",
        "group: esc-opportunity-cache-writer",
        "cancel-in-progress: false",
        "actions/checkout@v4",
        "actions/setup-python@v5",
        'python-version: "3.12"',
        "requests beautifulsoup4 pycountry",
        "python scraper/scraper.py",
        "MAX_BATCHES=3",
        "git add -- data/opportunities.json",
        "git add -- data/checkpoint.json",
        "git add -- data/expired.json",
        "git add -- web/opportunities.json",
        "git add -- web/expired.json",
        "git push origin main",
    ]

    missing = [fragment for fragment in required_fragments if fragment not in content]

    if missing:
        raise RuntimeError(
            "Generated workflow is missing required elements:\n"
            + "\n".join(f"  - {item}" for item in missing)
        )

    print("PASS: background workflow contains all required controls.")


def validate_workflow_safety():
    print("\nValidating workflow safety properties...")

    content = read_text(WORKFLOW_PATH)

    if "cancel-in-progress: true" in content:
        raise RuntimeError(
            "Background cache workflow must not cancel an active scraper run."
        )

    if "participant_country" in content.lower():
        raise RuntimeError(
            "Background workflow must not contain participant-country "
            "filtering logic."
        )

    if "git add ." in content:
        raise RuntimeError("Background workflow must not stage the entire repository.")

    if "git add --all" in content:
        raise RuntimeError("Background workflow must not stage the entire repository.")

    print(
        "PASS: workflow is country-agnostic and selectively stages "
        "scraper-generated cache files."
    )


def write_workflow():
    print("\nBuilding hourly background scraping workflow...")

    WORKFLOW_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    current = (
        WORKFLOW_PATH.read_text(encoding="utf-8") if WORKFLOW_PATH.exists() else None
    )

    if current == BACKGROUND_WORKFLOW:
        print("PASS: update.yml already matches the background architecture.")
        return

    WORKFLOW_PATH.write_text(
        BACKGROUND_WORKFLOW,
        encoding="utf-8",
    )

    print("PASS: .github/workflows/update.yml created/updated.")


def validate_python_syntax():
    print("\nRunning Python syntax validation...")

    python_files = [
        ROOT / "scraper/scraper.py",
        ROOT / "backend/cache.py",
        ROOT / "backend/search.py",
        ROOT / "backend/test_search.py",
        ROOT / "update.py",
    ]

    run(
        [
            sys.executable,
            "-m",
            "py_compile",
            *[str(path) for path in python_files],
        ]
    )

    print("PASS: Python syntax validation passed.")


def validate_json_files():
    print("\nValidating JSON cache files...")

    json_files = [
        ROOT / "data/opportunities.json",
        ROOT / "data/checkpoint.json",
        ROOT / "data/expired.json",
        ROOT / "web/opportunities.json",
        ROOT / "web/expired.json",
    ]

    for path in json_files:
        if not path.exists():
            print(f"NOTE: {path.relative_to(ROOT)} does not currently exist.")
            continue

        load_json(path)
        print(f"PASS: {path.relative_to(ROOT)} is valid JSON.")


def validate_whitespace():
    print("\nRunning Git whitespace check...")

    run(["git", "diff", "--check"])

    print("PASS: Git whitespace check passed.")


def stage_managed_files():
    print("\nPreparing selective background-scraper commit...")

    run(["git", "reset"])

    for relative in MANAGED_FILES:
        path = ROOT / relative

        if path.exists():
            run(["git", "add", "--", relative])

    staged = run(
        ["git", "diff", "--cached", "--name-only"],
        capture=True,
    ).stdout.splitlines()

    unexpected = sorted(set(staged) - set(MANAGED_FILES))

    if unexpected:
        raise RuntimeError(
            "Unexpected files are staged:\n"
            + "\n".join(f"  - {item}" for item in unexpected)
        )

    print("Files staged for this phase:")

    for item in staged:
        print(f"  {item}")

    return staged


def commit_and_push(staged):
    if not staged:
        print(
            "\nNo changes are required. " "Background workflow is already configured."
        )
        return False

    print("\nReviewing staged diff statistics...")
    run(["git", "diff", "--cached", "--stat"])

    print("\nCreating background scraper commit...")

    run(
        [
            "git",
            "commit",
            "-m",
            "feat: enable hourly ESC background scraping",
        ]
    )

    print("\nPushing background scraper workflow...")

    run(
        [
            "git",
            "push",
            "origin",
            "main",
        ]
    )

    print(
        "\nPASS: background scraping workflow configuration "
        "committed and pushed successfully."
    )

    return True


def main():
    print("=" * 72)
    print("ESC Opportunity Finder — Background Discovery Workflow")
    print("=" * 72)

    print("""This update will:
  - preserve the existing ESC scraper implementation
  - keep background discovery country-agnostic
  - run the scraper automatically every hour
  - use controlled incremental batches
  - install all scraper dependencies in GitHub Actions
  - preserve checkpoint/resumable scraping
  - stop safely when ESC rate-limits the scraper
  - publish the canonical cache to the website
  - serialize cache-writing workflow runs
  - stage only background-workflow files
  - validate Python and JSON files
  - commit and push the workflow configuration
""")

    try:
        require_files()
        check_git_state()
        check_branch()
        check_remote()

        validate_scraper_architecture()
        validate_scraper_is_country_agnostic()

        validate_existing_cache()

        write_workflow()

        validate_workflow()
        validate_workflow_safety()

        validate_python_syntax()
        validate_json_files()
        validate_whitespace()

        staged = stage_managed_files()
        commit_and_push(staged)

        print("\n" + "=" * 72)
        print("BACKGROUND SCRAPING PHASE COMPLETE")
        print("=" * 72)
        print()
        print(
            "GitHub Actions is now configured to run the ESC "
            "background scraper hourly."
        )
        print(
            "The scraper will continue accumulating data through "
            "data/checkpoint.json."
        )
        print(
            "The next phase can build on the resulting dataset "
            "without changing the discovery architecture."
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
