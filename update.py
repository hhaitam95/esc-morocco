#!/usr/bin/env python3

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent

REMOTE = "origin"
BRANCH = "main"

APP_JS = ROOT / "web" / "app.js"
DATA_PROVIDER_JS = ROOT / "web" / "data-provider.js"
INDEX_HTML = ROOT / "web" / "index.html"

SOURCE_DATA_JSON = ROOT / "data" / "opportunities.json"
WEB_DATA_JSON = ROOT / "web" / "opportunities.json"
REPAIR_CHECKPOINT = ROOT / "data" / "full_detail_repair_checkpoint.json"

REVIEW_MD = ROOT / "UPDATE_REVIEW.md"

EXPECTED_COUNT = 1178
TARGET_ID = "53577"

EXPECTED_STASH_PREFIX = "ESC-safe-worktree-"


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    print()
    print("No destructive cleanup was performed.")
    sys.exit(1)


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
            "Command failed with exit code " f"{result.returncode}: {' '.join(command)}"
        )

    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def validate_update_py() -> None:
    try:
        ast.parse(
            Path(__file__).read_text(encoding="utf-8"),
            filename=str(Path(__file__)),
        )
    except SyntaxError as exc:
        fail(f"update.py syntax error at line {exc.lineno}: " f"{exc.msg}")

    print("PASS: update.py syntax validated.")


def require_git_repository() -> None:
    if not (ROOT / ".git").exists():
        fail("This directory is not a Git repository.")

    repository_root = Path(
        run(
            ["git", "rev-parse", "--show-toplevel"],
            quiet=True,
        ).stdout.strip()
    ).resolve()

    if repository_root != ROOT.resolve():
        fail(
            "update.py is not located at the repository root.\n"
            f"Repository: {repository_root}\n"
            f"update.py:  {ROOT.resolve()}"
        )

    print(f"PASS: repository root validated: {ROOT}")


def current_branch() -> str:
    return run(
        ["git", "branch", "--show-current"],
        quiet=True,
    ).stdout.strip()


def require_main_branch() -> None:
    branch = current_branch()

    if branch != BRANCH:
        fail(f"Current branch is {branch!r}; expected {BRANCH!r}.")

    print("PASS: current branch is main.")


def status_lines() -> list[str]:
    result = run(
        ["git", "status", "--porcelain=v1"],
        quiet=True,
    )

    return [line for line in result.stdout.splitlines() if line.strip()]


def print_status(title: str) -> list[str]:
    status = status_lines()

    print()
    print(title)

    if status:
        for line in status:
            print(f"  {line}")
    else:
        print("  clean")

    return status


def fetch_origin() -> None:
    print()
    print("=" * 72)
    print("REFRESHING ORIGIN")
    print("=" * 72)

    run(
        ["git", "fetch", "--prune", REMOTE],
        check=True,
    )

    print("PASS: origin/main refreshed.")


def verify_not_behind_origin() -> None:
    local = run(
        ["git", "rev-parse", "main"],
        quiet=True,
    ).stdout.strip()

    remote = run(
        ["git", "rev-parse", "origin/main"],
        quiet=True,
    ).stdout.strip()

    print()
    print("Git history:")
    print(f"  main:        {local}")
    print(f"  origin/main: {remote}")

    behind = run(
        [
            "git",
            "rev-list",
            "--count",
            "main..origin/main",
        ],
        quiet=True,
    ).stdout.strip()

    if behind != "0":
        fail(
            "Local main is behind origin/main. "
            "Refusing to rewrite history while the in-progress "
            "dataset is present."
        )

    print("PASS: local main is not behind origin/main.")


def find_esc_safety_stash() -> str | None:
    result = run(
        ["git", "stash", "list"],
        quiet=True,
    )

    matches: list[str] = []

    for line in result.stdout.splitlines():
        if EXPECTED_STASH_PREFIX in line:
            matches.append(line)

    if not matches:
        return None

    if len(matches) > 1:
        print()
        print("WARNING: multiple ESC safety stashes exist.")

        for item in matches:
            print(f"  {item}")

        print("Using the newest matching stash. " "Older stashes will not be modified.")

    return matches[0].split(":", 1)[0].strip()


def detect_unmerged_files() -> set[str]:
    result = run(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=U",
        ],
        quiet=True,
    )

    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def unstage_everything_without_touching_worktree() -> None:
    staged = run(
        [
            "git",
            "diff",
            "--cached",
            "--name-only",
        ],
        quiet=True,
    ).stdout.strip()

    if not staged:
        print("PASS: nothing is staged before frontend changes.")
        return

    print()
    print("Unstaging restored work without changing file contents...")

    run(
        ["git", "reset"],
        check=True,
    )

    staged_after = run(
        [
            "git",
            "diff",
            "--cached",
            "--name-only",
        ],
        quiet=True,
    ).stdout.strip()

    if staged_after:
        fail("Files remain staged after unstage operation:\n" + staged_after)

    print("PASS: working-tree files preserved and index cleared.")


def resolve_current_stash_conflicts() -> None:
    conflicts = detect_unmerged_files()

    if not conflicts:
        print()
        print("PASS: no unresolved Git conflicts detected.")
        return

    print()
    print("=" * 72)
    print("RESOLVING PROTECTED DATASET CONFLICTS")
    print("=" * 72)

    expected = {
        "data/opportunities.json",
        "web/opportunities.json",
    }

    unexpected = conflicts - expected

    if unexpected:
        fail(
            "Unexpected merge conflicts exist:\n"
            + "\n".join(f"  - {item}" for item in sorted(unexpected))
        )

    if conflicts != expected:
        fail(
            "Expected both opportunity datasets to be conflicted.\n"
            "Current unresolved files:\n"
            + "\n".join(f"  - {item}" for item in sorted(conflicts))
        )

    stash_ref = find_esc_safety_stash()

    if stash_ref is None:
        fail(
            "The opportunity datasets are conflicted, but the protected "
            "ESC safety stash cannot be found."
        )

    print(f"Protected stash found: {stash_ref}")

    for relative_path in sorted(expected):
        print()
        print(f"Restoring protected local version of {relative_path}...")

        result = run(
            [
                "git",
                "checkout",
                "--theirs",
                "--",
                relative_path,
            ],
            check=False,
        )

        if result.returncode != 0:
            fail(f"Could not restore protected local version of " f"{relative_path}.")

        path = ROOT / relative_path

        if not path.exists():
            fail(f"{relative_path} disappeared while resolving the " "conflict.")

        run(
            [
                "git",
                "add",
                "--",
                relative_path,
            ],
            check=True,
        )

        print(f"PASS: preserved protected version of {relative_path}.")

    remaining = detect_unmerged_files()

    if remaining:
        fail(
            "Unmerged paths remain:\n"
            + "\n".join(f"  - {item}" for item in sorted(remaining))
        )

    print("PASS: opportunity dataset conflicts resolved.")

    # These restored files must remain ordinary working-tree changes.
    unstage_everything_without_touching_worktree()


def validate_json_file(path: Path) -> object:
    if not path.exists():
        fail(f"Required JSON file does not exist: {path}")

    source = path.read_text(encoding="utf-8")

    conflict_markers = (
        "<<<<<<< ",
        "=======",
        ">>>>>>> ",
    )

    found = [marker for marker in conflict_markers if marker in source]

    if found:
        fail(f"Git conflict markers remain in {path}: " + ", ".join(found))

    try:
        return json.loads(source)
    except Exception as exc:
        fail(f"Could not parse {path}: {exc}")

    raise AssertionError


def load_opportunity_payload(path: Path) -> tuple[dict, list[dict]]:
    payload = validate_json_file(path)

    if not isinstance(payload, dict):
        fail(f"{path} root must be a JSON object.")

    opportunities = payload.get("opportunities")

    if not isinstance(opportunities, list):
        fail(f"{path} does not contain an opportunities list.")

    valid_opportunities = [item for item in opportunities if isinstance(item, dict)]

    if len(valid_opportunities) != len(opportunities):
        fail(f"{path} contains non-object opportunity records.")

    return payload, opportunities


def validate_1178_dataset() -> tuple[dict, list[dict], dict]:
    print()
    print("=" * 72)
    print("VALIDATING LOCAL 1,178-OPPORTUNITY DATASET")
    print("=" * 72)

    if not SOURCE_DATA_JSON.exists():
        fail(
            "data/opportunities.json is missing. "
            "The local repaired backend dataset cannot be treated "
            "as authoritative."
        )

    if not WEB_DATA_JSON.exists():
        fail("web/opportunities.json is missing.")

    source_payload, source_opportunities = load_opportunity_payload(SOURCE_DATA_JSON)

    web_payload, web_opportunities = load_opportunity_payload(WEB_DATA_JSON)

    if len(source_opportunities) != EXPECTED_COUNT:
        fail(
            "data/opportunities.json does not contain the expected "
            f"{EXPECTED_COUNT} opportunities. "
            f"Found {len(source_opportunities)}."
        )

    if len(web_opportunities) != EXPECTED_COUNT:
        fail(
            "web/opportunities.json does not contain the expected "
            f"{EXPECTED_COUNT} opportunities. "
            f"Found {len(web_opportunities)}."
        )

    source_ids = {str(item.get("id")) for item in source_opportunities}

    web_ids = {str(item.get("id")) for item in web_opportunities}

    if source_ids != web_ids:
        missing = sorted(source_ids - web_ids)
        extra = sorted(web_ids - source_ids)

        fail(
            "data/opportunities.json and web/opportunities.json do "
            "not contain the same opportunity IDs.\n"
            f"Missing from web: {missing[:20]}\n"
            f"Extra in web: {extra[:20]}"
        )

    target = next(
        (item for item in web_opportunities if str(item.get("id")) == TARGET_ID),
        None,
    )

    if target is None:
        fail(f"Opportunity {TARGET_ID} was not found in " "web/opportunities.json.")

    dates = target.get("activity_dates")

    if not isinstance(dates, dict):
        fail(f"Opportunity {TARGET_ID} has no activity_dates object.")

    expected_values = {
        "activity_dates.start": (
            dates.get("start"),
            "2026-09-28",
        ),
        "activity_dates.end": (
            dates.get("end"),
            "2026-11-01",
        ),
        "application_deadline": (
            target.get("application_deadline"),
            "2026-08-20",
        ),
        "activity_type": (
            target.get("activity_type"),
            "Individual volunteering",
        ),
    }

    for field, (actual, expected) in expected_values.items():
        if actual != expected:
            fail(
                f"Opportunity {TARGET_ID} {field} is incorrect.\n"
                f"Actual:   {actual!r}\n"
                f"Expected: {expected!r}"
            )

    if not target.get("logo_url"):
        fail(f"Opportunity {TARGET_ID} has no logo_url.")

    if not target.get("location"):
        fail(f"Opportunity {TARGET_ID} has no location.")

    print(f"PASS: data/opportunities.json contains " f"{EXPECTED_COUNT} opportunities.")

    print(f"PASS: web/opportunities.json contains " f"{EXPECTED_COUNT} opportunities.")

    print("PASS: backend/frontend opportunity ID sets match.")

    print(f"PASS: opportunity {TARGET_ID} validated.")

    print("     activity_dates: 2026-09-28 -> 2026-11-01")

    print("     application_deadline: 2026-08-20")

    print("     activity_type: Individual volunteering")

    print("     logo_url: present")
    print("     location: present")

    return web_payload, web_opportunities, target


def validate_checkpoint() -> str:
    if not REPAIR_CHECKPOINT.exists():
        fail("data/full_detail_repair_checkpoint.json is missing.")

    source = REPAIR_CHECKPOINT.read_text(encoding="utf-8")

    conflict_markers = (
        "<<<<<<< ",
        "=======",
        ">>>>>>> ",
    )

    if any(marker in source for marker in conflict_markers):
        fail("full_detail_repair_checkpoint.json contains Git " "conflict markers.")

    try:
        payload = json.loads(source)
    except Exception as exc:
        fail("full_detail_repair_checkpoint.json is not valid JSON: " f"{exc}")

    if not isinstance(payload, (dict, list)):
        fail("full_detail_repair_checkpoint.json has an unsupported " "root type.")

    checkpoint_hash = sha256(REPAIR_CHECKPOINT)

    print()
    print("PASS: full_detail_repair_checkpoint.json is valid.")
    print(f"     size: {REPAIR_CHECKPOINT.stat().st_size} bytes")
    print(f"     sha256: {checkpoint_hash}")

    return checkpoint_hash


def replace_block(
    source: str,
    old: str,
    new: str,
    description: str,
) -> tuple[str, bool]:
    if old in source:
        return source.replace(old, new, 1), True

    if new in source:
        return source, False

    fail(f"Could not locate expected source block while " f"updating {description}.")

    raise AssertionError


def build_provider_source() -> str:
    lines = [
        "// ESC Opportunity Finder — static backend data provider",
        "//",
        "// GitHub Pages is a static frontend, so the published backend",
        "// dataset is consumed from web/opportunities.json.",
        "//",
        "// The backend scraper remains the source of truth.",
        "// This provider is the browser-side boundary between that",
        "// generated dataset and web/app.js.",
        "",
        "window.ESC_DATA_PROVIDER = {",
        "  enabled: true,",
        "",
        "  async load() {",
        "    const response = await fetch(",
        "      `./opportunities.json?v=${Date.now()}`,",
        "      {",
        "        cache: 'no-store',",
        "      },",
        "    );",
        "",
        "    if (!response.ok) {",
        "      throw new Error(",
        "        `Could not load opportunities.json (${response.status})`,",
        "      );",
        "    }",
        "",
        "    const payload = await response.json();",
        "",
        "    if (!payload || typeof payload !== 'object') {",
        "      throw new Error('Opportunity dataset has an invalid root object.');",
        "    }",
        "",
        "    const sourceOpportunities = Array.isArray(payload.opportunities)",
        "      ? payload.opportunities",
        "      : [];",
        "",
        "    if (!sourceOpportunities.length) {",
        "      throw new Error('Opportunity dataset contains no opportunities.');",
        "    }",
        "",
        "    const today = new Date();",
        "    today.setHours(0, 0, 0, 0);",
        "",
        "    const recentExpiredCutoff = new Date(today);",
        "    recentExpiredCutoff.setDate(",
        "      recentExpiredCutoff.getDate() - 30,",
        "    );",
        "",
        "    const normalizeCode = (value) =>",
        "      String(value || '')",
        "        .trim()",
        "        .toUpperCase();",
        "",
        "    const normalizeOpportunity = (opportunity) => {",
        "      const item = { ...opportunity };",
        "",
        "      const dates =",
        "        item.activity_dates &&",
        "        typeof item.activity_dates === 'object'",
        "          ? item.activity_dates",
        "          : {};",
        "",
        "      item.start_date =",
        "        dates.start ||",
        "        item.start_date ||",
        "        '';",
        "",
        "      item.end_date =",
        "        dates.end ||",
        "        item.end_date ||",
        "        '';",
        "",
        "      item.deadline =",
        "        item.application_deadline ||",
        "        item.deadline ||",
        "        '';",
        "",
        "      item.image_url =",
        "        item.logo_url ||",
        "        item.image_url ||",
        "        '';",
        "",
        "      item.town =",
        "        item.town ||",
        "        item.city ||",
        "        '';",
        "",
        "      const participantCountries =",
        "        Array.isArray(item.participant_countries)",
        "          ? item.participant_countries",
        "          : Array.isArray(item.eligible_countries)",
        "            ? item.eligible_countries",
        "            : [];",
        "",
        "      item.participant_countries = [",
        "        ...new Set(",
        "          participantCountries",
        "            .map(normalizeCode)",
        "            .filter(Boolean),",
        "        ),",
        "      ];",
        "",
        "      item.eligible_countries = [",
        "        ...new Set(",
        "          (Array.isArray(item.eligible_countries)",
        "            ? item.eligible_countries",
        "            : item.participant_countries",
        "          )",
        "            .map(normalizeCode)",
        "            .filter(Boolean),",
        "        ),",
        "      ];",
        "",
        "      return item;",
        "    };",
        "",
        "    const normalized = sourceOpportunities",
        "      .filter(",
        "        (item) => item && typeof item === 'object',",
        "      )",
        "      .map(normalizeOpportunity);",
        "",
        "    const activeOpportunities = [];",
        "    const recentlyExpired = [];",
        "",
        "    normalized.forEach((opportunity) => {",
        "      const deadline = String(opportunity.deadline || '').trim();",
        "",
        "      if (!deadline) {",
        "        activeOpportunities.push(opportunity);",
        "        return;",
        "      }",
        "",
        "      const deadlineDate = new Date(`${deadline}T23:59:59`);",
        "",
        "      if (Number.isNaN(deadlineDate.getTime())) {",
        "        activeOpportunities.push(opportunity);",
        "        return;",
        "      }",
        "",
        "      if (deadlineDate >= today) {",
        "        activeOpportunities.push(opportunity);",
        "        return;",
        "      }",
        "",
        "      if (deadlineDate >= recentExpiredCutoff) {",
        "        recentlyExpired.push(opportunity);",
        "      }",
        "    });",
        "",
        "    const participantCountryIndex = {};",
        "",
        "    activeOpportunities.forEach((opportunity) => {",
        "      const opportunityId = String(",
        "        opportunity.id ?? opportunity.opid ?? '',",
        "      );",
        "",
        "      opportunity.participant_countries.forEach((code) => {",
        "        if (!participantCountryIndex[code]) {",
        "          participantCountryIndex[code] = [];",
        "        }",
        "",
        "        participantCountryIndex[code].push(opportunityId);",
        "      });",
        "    });",
        "",
        "    Object.keys(participantCountryIndex).forEach((code) => {",
        "      participantCountryIndex[code] = [",
        "        ...new Set(participantCountryIndex[code]),",
        "      ];",
        "    });",
        "",
        "    const activeData = {",
        "      ...payload,",
        "      opportunities: activeOpportunities,",
        "      count: activeOpportunities.length,",
        "    };",
        "",
        "    const expiredData = {",
        "      ...payload,",
        "      opportunities: recentlyExpired,",
        "      count: recentlyExpired.length,",
        "    };",
        "",
        "    return {",
        "      activeData,",
        "      expiredData,",
        "      participantCountryIndex,",
        "    };",
        "  },",
        "};",
    ]

    return "\n".join(lines) + "\n"


def write_provider() -> None:
    DATA_PROVIDER_JS.write_text(
        build_provider_source(),
        encoding="utf-8",
    )

    print("PASS: web/data-provider.js connected to " "web/opportunities.json.")


def patch_app_js() -> tuple[str, bool]:
    source = APP_JS.read_text(encoding="utf-8")
    original = source

    if "let availableActiveOpportunities = [];" not in source:
        old = "let activeOpportunities = [];\nlet expiredOpportunities = [];"
        new = (
            "let activeOpportunities = [];\n"
            "let availableActiveOpportunities = [];\n"
            "let expiredOpportunities = [];"
        )

        source, _ = replace_block(
            source,
            old,
            new,
            "available opportunity state",
        )

    old_normalizer = """function normalizeLoadedOpportunity(opportunity) {
  if (!opportunity || typeof opportunity !== "object") {
    return opportunity;
  }

  const dates =
    opportunity.activity_dates &&
    typeof opportunity.activity_dates === "object"
      ? opportunity.activity_dates
      : {};

  const startDate =
    dates.start ||
    opportunity.start_date ||
    "";

  const endDate =
    dates.end ||
    opportunity.end_date ||
    "";

  const deadline =
    opportunity.application_deadline ||
    opportunity.deadline ||
    "";

  const logo =
    opportunity.logo_url ||
    opportunity.image_url ||
    "";

  const rawLocation = String(
    opportunity.location || ""
  ).trim();

  let city = "";
  let country = "";

  const locationParts = rawLocation
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);

  if (locationParts.length >= 2) {
    country = locationParts[locationParts.length - 1];
    city = locationParts[locationParts.length - 2];
  }

  opportunity.image_url = logo;
  opportunity.logoUrl = logo;

  opportunity.start_date = startDate;
  opportunity.end_date = endDate;
  opportunity.startDate = startDate;
  opportunity.endDate = endDate;

  opportunity.deadline = deadline;
  opportunity.applicationDeadline = deadline;

  opportunity.town = city;
  opportunity.city = city;
  opportunity.country = country;

  opportunity.location_full = rawLocation;

  if (city && country) {
    opportunity.location = `${city}, ${country}`;
  }

  return opportunity;
}"""

    new_normalizer = """function normalizeLoadedOpportunity(opportunity) {
  if (!opportunity || typeof opportunity !== "object") {
    return opportunity;
  }

  const dates =
    opportunity.activity_dates &&
    typeof opportunity.activity_dates === "object"
      ? opportunity.activity_dates
      : {};

  const startDate =
    dates.start ||
    opportunity.start_date ||
    "";

  const endDate =
    dates.end ||
    opportunity.end_date ||
    "";

  const deadline =
    opportunity.application_deadline ||
    opportunity.deadline ||
    "";

  const logo =
    opportunity.logo_url ||
    opportunity.image_url ||
    "";

  const rawLocation = String(
    opportunity.location || ""
  ).trim();

  const existingCountry = String(
    opportunity.country || ""
  ).trim();

  let city =
    String(
      opportunity.town ||
      opportunity.city ||
      ""
    ).trim();

  let inferredCountryName = "";

  const locationParts = rawLocation
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);

  if (!city && locationParts.length >= 2) {
    city = locationParts[locationParts.length - 2];
  }

  if (locationParts.length >= 2) {
    inferredCountryName =
      locationParts[locationParts.length - 1];
  }

  opportunity.image_url = logo;
  opportunity.logoUrl = logo;

  opportunity.start_date = startDate;
  opportunity.end_date = endDate;
  opportunity.startDate = startDate;
  opportunity.endDate = endDate;

  opportunity.deadline = deadline;
  opportunity.applicationDeadline = deadline;

  opportunity.town = city;
  opportunity.city = city;

  // Preserve a backend country code such as "TR", "FR", or "MA".
  // The previous compatibility mapper incorrectly overwrote these
  // codes with the human-readable country name parsed from location.
  if (/^[A-Za-z]{2}$/.test(existingCountry)) {
    opportunity.country =
      existingCountry.toUpperCase();
  } else if (!existingCountry && inferredCountryName) {
    opportunity.country = inferredCountryName;
  } else {
    opportunity.country = existingCountry;
  }

  opportunity.location_full = rawLocation;

  return opportunity;
}"""

    source, normalizer_changed = replace_block(
        source,
        old_normalizer,
        new_normalizer,
        "opportunity compatibility normalizer",
    )

    old_apply_filter = """    const matchingOpportunities =
      Array.isArray(activeOpportunities)
        ? activeOpportunities.filter(
            (opportunity) =>
              Array.isArray(
                opportunity.participant_countries,
              ) &&
              opportunity.participant_countries.includes(
                selectedCode,
              ),
          )
        : [];

    activeOpportunities =
      matchingOpportunities;"""

    new_apply_filter = """    const matchingOpportunities =
      Array.isArray(availableActiveOpportunities)
        ? availableActiveOpportunities.filter(
            (opportunity) => {
              const participantCountries =
                Array.isArray(
                  opportunity.participant_countries,
                )
                  ? opportunity.participant_countries
                  : Array.isArray(
                        opportunity.eligible_countries,
                      )
                    ? opportunity.eligible_countries
                    : [];

              return participantCountries
                .map((value) =>
                  String(value || "")
                    .trim()
                    .toUpperCase()
                )
                .includes(selectedCode);
            },
          )
        : [];

    activeOpportunities =
      matchingOpportunities;"""

    source, apply_changed = replace_block(
        source,
        old_apply_filter,
        new_apply_filter,
        "participant-country filtering",
    )

    old_no_search = """  if (!participantSearchApplied) {
    resetParticipantSearchDisplay();
    errorMessage.classList.add("hidden");
    return;
  }"""

    new_no_search = """  if (!participantSearchApplied) {
    activeOpportunities = [
      ...availableActiveOpportunities,
    ];

    resetParticipantSearchDisplay();
    errorMessage.classList.add("hidden");
    return;
  }"""

    source, no_search_changed = replace_block(
        source,
        old_no_search,
        new_no_search,
        "participant search reset",
    )

    old_load_assignment = """    activeOpportunities =
      normalizeLoadedOpportunities(
        Array.isArray(payload?.activeData?.opportunities)
          ? payload.activeData.opportunities
          : [],
      );"""

    new_load_assignment = """    availableActiveOpportunities =
      normalizeLoadedOpportunities(
        Array.isArray(payload?.activeData?.opportunities)
          ? payload.activeData.opportunities
          : [],
      );

    activeOpportunities = [
      ...availableActiveOpportunities,
    ];"""

    source, load_assignment_changed = replace_block(
        source,
        old_load_assignment,
        new_load_assignment,
        "loadData opportunity assignment",
    )

    changed = (
        source != original
        or normalizer_changed
        or apply_changed
        or no_search_changed
        or load_assignment_changed
    )

    return source, changed


def patch_app_js_file() -> None:
    updated, changed = patch_app_js()

    if changed:
        APP_JS.write_text(
            updated,
            encoding="utf-8",
        )

        print(
            "PASS: web/app.js updated for real opportunity loading "
            "and participant-country filtering."
        )
    else:
        print("PASS: web/app.js already contains the required " "frontend wiring.")


def patch_index_html() -> None:
    source = INDEX_HTML.read_text(encoding="utf-8")

    original = source

    duplicated = """    <script src="features.js?v=1"></script>
<script src="data-provider.js?v=1"></script>
<script src="features.js?v=1"></script>
<script src="data-provider.js?v=1"></script>
<script src="app.js?v=22"></script>"""

    corrected = """    <script src="features.js?v=1"></script>
    <script src="data-provider.js?v=2"></script>
    <script src="app.js?v=23"></script>"""

    if duplicated in source:
        source = source.replace(
            duplicated,
            corrected,
            1,
        )
    else:
        # Normalize any existing duplicated provider/feature block.
        script_pattern = re.compile(
            r'\s*<script src="features\.js\?v=1"></script>'
            r'\s*<script src="data-provider\.js\?v=\d+"></script>'
            r'\s*<script src="features\.js\?v=1"></script>'
            r'\s*<script src="data-provider\.js\?v=\d+"></script>'
            r'\s*<script src="app\.js\?v=\d+"></script>',
            re.MULTILINE,
        )

        source, replacements = script_pattern.subn(
            "\n"
            '    <script src="features.js?v=1"></script>\n'
            '    <script src="data-provider.js?v=2"></script>\n'
            '    <script src="app.js?v=23"></script>',
            source,
            count=1,
        )

        if replacements == 0:
            # The remote version may already have been manually cleaned.
            if (
                source.count('src="features.js?v=1"') == 1
                and source.count('src="data-provider.js?v=2"') == 1
                and source.count('src="app.js?v=23"') == 1
            ):
                pass
            else:
                fail("Could not locate the frontend script block in " "web/index.html.")

    feature_count = source.count('src="features.js?v=1"')
    provider_count = source.count('src="data-provider.js?v=2"')
    app_count = source.count('src="app.js?v=23"')

    if feature_count != 1:
        fail("web/index.html must load features.js exactly once.")

    if provider_count != 1:
        fail("web/index.html must load data-provider.js exactly once.")

    if app_count != 1:
        fail("web/index.html must load app.js exactly once.")

    if source != original:
        INDEX_HTML.write_text(
            source,
            encoding="utf-8",
        )

        print(
            "PASS: duplicate frontend scripts removed and "
            "cache-busting versions updated."
        )
    else:
        print("PASS: web/index.html script loading already normalized.")


def node_check(path: Path) -> None:
    result = run(
        [
            "node",
            "--check",
            str(path),
        ],
        check=False,
    )

    if result.returncode != 0:
        fail(f"{path} failed Node.js syntax validation.")

    print(f"PASS: {path.relative_to(ROOT)} syntax validated.")


def validate_provider_source() -> None:
    source = DATA_PROVIDER_JS.read_text(encoding="utf-8")

    required = [
        "window.ESC_DATA_PROVIDER",
        "enabled: true",
        "fetch(",
        "./opportunities.json",
        "activeData",
        "expiredData",
        "participantCountryIndex",
        "participant_countries",
        "eligible_countries",
    ]

    missing = [item for item in required if item not in source]

    if missing:
        fail(
            "data-provider.js validation failed. Missing:\n"
            + "\n".join(f"  - {item}" for item in missing)
        )

    print(
        "PASS: data-provider.js is configured for the " "published opportunity dataset."
    )


def validate_app_source() -> None:
    source = APP_JS.read_text(encoding="utf-8")

    required = [
        "let availableActiveOpportunities = [];",
        "Array.isArray(availableActiveOpportunities)",
        "participant_countries",
        "eligible_countries",
        "availableActiveOpportunities =",
        "normalizeLoadedOpportunities(",
    ]

    missing = [item for item in required if item not in source]

    if missing:
        fail(
            "web/app.js validation failed. Missing:\n"
            + "\n".join(f"  - {item}" for item in missing)
        )

    print("PASS: app.js participant-country and dataset wiring validated.")


def validate_country_selector() -> None:
    source = APP_JS.read_text(encoding="utf-8")

    marker = "const ESC_PARTICIPANT_COUNTRIES = ["

    start = source.find(marker)

    if start == -1:
        fail("Could not locate ESC_PARTICIPANT_COUNTRIES.")

    end = source.find(
        "];",
        start,
    )

    if end == -1:
        fail("Could not determine end of participant country list.")

    block = source[start:end]

    matches = re.findall(
        r"\{\s*name:\s*",
        block,
    )

    if len(matches) != 65:
        fail(
            "Expected 65 participant countries in frontend selector; "
            f"found {len(matches)}."
        )

    print("PASS: frontend participant-country selector contains " "65 countries.")


def validate_participant_eligibility_data(
    opportunities: list[dict],
) -> tuple[str, int]:
    country_counts: dict[str, int] = {}

    for opportunity in opportunities:
        countries = (
            opportunity.get("participant_countries")
            if isinstance(
                opportunity.get("participant_countries"),
                list,
            )
            else opportunity.get("eligible_countries")
        )

        if not isinstance(countries, list):
            continue

        for country in countries:
            code = str(country).strip().upper()

            if not code:
                continue

            country_counts[code] = country_counts.get(code, 0) + 1

    if not country_counts:
        fail(
            "The 1,178-opportunity dataset contains no participant "
            "eligibility country data."
        )

    if country_counts.get("MA", 0) <= 0:
        fail(
            "The 1,178-opportunity dataset contains no opportunities "
            "eligible for Morocco (MA)."
        )

    non_morocco = sorted(
        (
            (code, count)
            for code, count in country_counts.items()
            if code != "MA" and count > 0
        ),
        key=lambda item: (-item[1], item[0]),
    )

    if not non_morocco:
        fail("No non-Morocco participant country has eligibility data.")

    sample_code, sample_count = non_morocco[0]

    print(
        f"PASS: Morocco eligibility data present "
        f"({country_counts['MA']} opportunities)."
    )

    print("PASS: non-Morocco eligibility data present.")

    print(f"     sample country: {sample_code} " f"({sample_count} opportunities)")

    print(
        f"PASS: eligibility data covers {len(country_counts)} "
        "participant-country codes."
    )

    return sample_code, sample_count


def simulate_frontend_mapping(target: dict) -> None:
    dates = target.get("activity_dates")

    if not isinstance(dates, dict):
        fail("Target opportunity activity_dates missing.")

    start = dates.get("start")
    end = dates.get("end")
    deadline = target.get("application_deadline")

    raw_location = str(target.get("location") or "").strip()

    parts = [part.strip() for part in raw_location.split(",") if part.strip()]

    inferred_city = parts[-2] if len(parts) >= 2 else ""

    if inferred_city != "TANDOGAN ANKARA":
        fail("Target 53577 city simulation failed: " + repr(inferred_city))

    if start != "2026-09-28":
        fail("Target 53577 start-date simulation failed.")

    if end != "2026-11-01":
        fail("Target 53577 end-date simulation failed.")

    if deadline != "2026-08-20":
        fail("Target 53577 deadline simulation failed.")

    if not target.get("logo_url"):
        fail("Target 53577 logo simulation failed.")

    print("PASS: opportunity 53577 frontend compatibility simulation.")

    print("     town: TANDOGAN ANKARA")

    print("     dates: 2026-09-28 -> 2026-11-01")

    print("     deadline: 2026-08-20")

    print("     logo: present")


def test_provider_with_node(
    payload: dict,
) -> None:
    provider_source = DATA_PROVIDER_JS.read_text(encoding="utf-8")

    encoded_payload = json.dumps(
        payload,
        ensure_ascii=False,
    )

    harness_lines = [
        "const fs = require('fs');",
        "",
        "global.window = {};",
        "",
        "const payload = " + encoded_payload + ";",
        "",
        "global.fetch = async () => ({",
        "  ok: true,",
        "  status: 200,",
        "  async json() {",
        "    return payload;",
        "  },",
        "});",
        "",
        provider_source,
        "",
        "(async () => {",
        "  const result = await window.ESC_DATA_PROVIDER.load();",
        "",
        "  if (!result || !result.activeData) {",
        "    throw new Error('activeData missing');",
        "  }",
        "",
        "  if (!result.expiredData) {",
        "    throw new Error('expiredData missing');",
        "  }",
        "",
        "  if (!result.participantCountryIndex) {",
        "    throw new Error('participantCountryIndex missing');",
        "  }",
        "",
        "  if (!Array.isArray(result.activeData.opportunities)) {",
        "    throw new Error('active opportunities are not an array');",
        "  }",
        "",
        "  if (result.activeData.opportunities.length === 0) {",
        "    throw new Error('active opportunities are empty');",
        "  }",
        "",
        "  const sample = result.activeData.opportunities[0];",
        "",
        "  if (!Array.isArray(sample.participant_countries)) {",
        "    throw new Error('participant_countries missing');",
        "  }",
        "",
        "  if (!('deadline' in sample)) {",
        "    throw new Error('deadline mapping missing');",
        "  }",
        "",
        "  if (!('image_url' in sample)) {",
        "    throw new Error('image_url mapping missing');",
        "  }",
        "",
        "  console.log('PASS: provider runtime simulation loaded active data.');",
        "  console.log(`     active opportunities: ${result.activeData.count}`);",
        "  console.log(`     recently expired: ${result.expiredData.count}`);",
        "  console.log(`     participant country codes indexed: ${Object.keys(result.participantCountryIndex).length}`);",
        "})().catch((error) => {",
        "  console.error(error);",
        "  process.exit(1);",
        "});",
    ]

    temporary = ROOT / ".esc_provider_check.js"

    temporary.write_text(
        "\n".join(harness_lines),
        encoding="utf-8",
    )

    try:
        result = run(
            [
                "node",
                str(temporary),
            ],
            check=False,
        )

        if result.returncode != 0:
            fail("data-provider.js runtime simulation failed.")
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def write_review(
    *,
    before_app: str,
    before_provider: str,
    before_index: str,
    after_app: str,
    after_provider: str,
    after_index: str,
    participant_country_sample: str,
    participant_country_sample_count: int,
) -> None:
    diff_result = run(
        [
            "git",
            "diff",
            "--",
            "web/app.js",
            "web/data-provider.js",
            "web/index.html",
            "data/opportunities.json",
            "web/opportunities.json",
            "update.py",
        ],
        quiet=True,
    )

    diff = diff_result.stdout

    lines = [
        "# ESC Opportunity Finder — Connect Backend Dataset to Frontend",
        "",
        "## Scope",
        "",
        "The local 1,178-opportunity dataset is treated as authoritative.",
        "",
        "The frontend now reads the published `web/opportunities.json` "
        "through `web/data-provider.js`.",
        "",
        "The participant-country selector filters the loaded active "
        "dataset using `participant_countries` or `eligible_countries`.",
        "",
        "No scraper rate limits, retry behaviour, batch sizes, or workflow "
        "scheduling were changed.",
        "",
        "The repair checkpoint was intentionally not committed.",
        "",
        "## Dataset validation",
        "",
        f"- `data/opportunities.json`: {EXPECTED_COUNT} opportunities",
        f"- `web/opportunities.json`: {EXPECTED_COUNT} opportunities",
        "- Backend/frontend opportunity ID sets: identical",
        f"- Opportunity {TARGET_ID}: PASS",
        "- Activity dates: PASS",
        "- Application deadline: PASS",
        "- Logo: PASS",
        "- Participant eligibility data: PASS",
        f"- Morocco eligibility count: validated",
        f"- Non-Morocco sample: {participant_country_sample} "
        f"({participant_country_sample_count} opportunities)",
        "",
        "## Frontend integration",
        "",
        "- `data-provider.js` enabled",
        "- `opportunities.json` loaded through `fetch()`",
        "- active opportunities split from recently expired opportunities",
        "- participant-country index created client-side",
        "- `eligible_countries` compatibility supported",
        "- 65-country selector preserved",
        "- frontend country code preservation fixed",
        "- duplicate script loading removed from `index.html`",
        "",
        "## Validation",
        "",
        "- update.py syntax: PASS",
        "- provider syntax: PASS",
        "- provider runtime simulation: PASS",
        "- app.js syntax: PASS",
        "- index.html script counts: PASS",
        "- dataset JSON: PASS",
        "- repair checkpoint: PASS",
        "",
        "## Source snapshot sizes",
        "",
        f"- app.js before: {len(before_app)} characters",
        f"- app.js after: {len(after_app)} characters",
        f"- data-provider.js before: {len(before_provider)} characters",
        f"- data-provider.js after: {len(after_provider)} characters",
        f"- index.html before: {len(before_index)} characters",
        f"- index.html after: {len(after_index)} characters",
        "",
        "## Git diff",
        "",
        "```diff",
        diff.rstrip(),
        "```",
        "",
    ]

    REVIEW_MD.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print(f"PASS: review file written: {REVIEW_MD}")


def stage_allowed_files() -> None:
    allowed = {
        "data/opportunities.json",
        "web/opportunities.json",
        "web/app.js",
        "web/data-provider.js",
        "web/index.html",
        "update.py",
        "UPDATE_REVIEW.md",
    }

    print()
    print("=" * 72)
    print("STAGING FRONTEND/BACKEND DATA INTEGRATION")
    print("=" * 72)

    run(
        [
            "git",
            "add",
            "--",
            *sorted(allowed),
        ],
        check=True,
    )

    staged_result = run(
        [
            "git",
            "diff",
            "--cached",
            "--name-only",
        ],
        quiet=True,
    )

    staged = {
        line.strip() for line in staged_result.stdout.splitlines() if line.strip()
    }

    unexpected = staged - allowed

    if unexpected:
        run(
            ["git", "reset"],
            check=False,
        )

        fail(
            "Unexpected files were staged:\n"
            + "\n".join(f"  - {item}" for item in sorted(unexpected))
        )

    required = {
        "data/opportunities.json",
        "web/opportunities.json",
        "web/app.js",
        "web/data-provider.js",
        "web/index.html",
        "update.py",
        "UPDATE_REVIEW.md",
    }

    missing = required - staged

    if missing:
        run(
            ["git", "reset"],
            check=False,
        )

        fail(
            "Required files were not staged:\n"
            + "\n".join(f"  - {item}" for item in sorted(missing))
        )

    print("PASS: only intended integration files are staged.")

    for item in sorted(staged):
        print(f"  - {item}")

    if REPAIR_CHECKPOINT.exists():
        checkpoint_result = run(
            [
                "git",
                "diff",
                "--cached",
                "--name-only",
            ],
            quiet=True,
        ).stdout

        if "data/full_detail_repair_checkpoint.json" in checkpoint_result:
            run(
                [
                    "git",
                    "reset",
                    "--",
                    "data/full_detail_repair_checkpoint.json",
                ],
                check=True,
            )

            fail("Repair checkpoint was unexpectedly staged.")

    print("PASS: repair checkpoint is not staged.")


def commit_changes() -> None:
    print()
    print("=" * 72)
    print("COMMITTING BACKEND/FRONTEND CONNECTION")
    print("=" * 72)

    run(
        [
            "git",
            "commit",
            "-m",
            "Connect frontend to full opportunity dataset",
        ],
        check=True,
    )

    print("PASS: integration commit created.")


def push_main() -> None:
    print()
    print("=" * 72)
    print("PUSHING TO ORIGIN/MAIN")
    print("=" * 72)

    fetch_origin()
    verify_not_behind_origin()

    run(
        [
            "git",
            "push",
            REMOTE,
            BRANCH,
        ],
        check=True,
    )

    print("PASS: main pushed to origin/main.")


def verify_final_state() -> None:
    print()
    print("=" * 72)
    print("FINAL VALIDATION")
    print("=" * 72)

    local = run(
        [
            "git",
            "rev-parse",
            "main",
        ],
        quiet=True,
    ).stdout.strip()

    remote = run(
        [
            "git",
            "rev-parse",
            "origin/main",
        ],
        quiet=True,
    ).stdout.strip()

    if local != remote:
        fail("Final main and origin/main SHA values differ.")

    print("PASS: local main == origin/main.")

    conflicts = detect_unmerged_files()

    if conflicts:
        fail(
            "Final state still contains unresolved conflicts:\n"
            + "\n".join(f"  - {item}" for item in sorted(conflicts))
        )

    print("PASS: no unresolved Git conflicts remain.")

    status = print_status("FINAL WORKTREE:")

    checkpoint_staged = run(
        [
            "git",
            "diff",
            "--cached",
            "--name-only",
        ],
        quiet=True,
    ).stdout

    if "data/full_detail_repair_checkpoint.json" in checkpoint_staged:
        fail("Repair checkpoint is staged unexpectedly.")

    if any(
        line.startswith(
            (
                "UU ",
                "AA ",
                "DD ",
                "AU ",
                "UA ",
                "DU ",
            )
        )
        for line in status
    ):
        fail("Final Git status still reports unresolved merge state.")

    print("PASS: repair checkpoint remains outside the staged commit.")

    stash_ref = find_esc_safety_stash()

    if stash_ref:
        print()
        print(f"PASS: original safety stash retained: {stash_ref}")

        print("     It was intentionally not deleted automatically.")

    print()
    print("Final main SHA:")
    print(local)


def main() -> None:
    print("=" * 72)
    print("ESC Opportunity Finder — connect full backend dataset to frontend")
    print("=" * 72)
    print()

    validate_update_py()
    require_git_repository()
    require_main_branch()

    status_before = print_status("CURRENT WORKTREE:")

    checkpoint_before = (
        sha256(REPAIR_CHECKPOINT) if REPAIR_CHECKPOINT.exists() else None
    )

    fetch_origin()
    verify_not_behind_origin()

    resolve_current_stash_conflicts()

    # Clear any staging left behind by the interrupted stash-pop.
    unstage_everything_without_touching_worktree()

    (
        web_payload,
        web_opportunities,
        target,
    ) = validate_1178_dataset()

    checkpoint_hash = validate_checkpoint()

    if checkpoint_before is not None:
        if checkpoint_hash != checkpoint_before:
            fail(
                "full_detail_repair_checkpoint.json changed while "
                "resolving the previous stash conflict."
            )

        print("PASS: repair checkpoint SHA-256 unchanged.")

    participant_country_sample, participant_country_sample_count = (
        validate_participant_eligibility_data(web_opportunities)
    )

    simulate_frontend_mapping(target)

    before_app = APP_JS.read_text(encoding="utf-8")

    before_provider = DATA_PROVIDER_JS.read_text(encoding="utf-8")

    before_index = INDEX_HTML.read_text(encoding="utf-8")

    print()
    print("=" * 72)
    print("CONNECTING FRONTEND TO FULL DATASET")
    print("=" * 72)

    patch_app_js_file()
    write_provider()
    patch_index_html()

    node_check(APP_JS)
    node_check(DATA_PROVIDER_JS)

    validate_provider_source()
    validate_app_source()
    validate_country_selector()

    provider_payload = {
        key: web_payload[key] for key in web_payload if key != "opportunities"
    }

    provider_payload["opportunities"] = web_opportunities

    test_provider_with_node(provider_payload)

    # Validate that the data files were not modified by frontend code
    # generation.
    _, source_after = load_opportunity_payload(SOURCE_DATA_JSON)

    web_payload_after, web_after = load_opportunity_payload(WEB_DATA_JSON)

    if len(source_after) != EXPECTED_COUNT:
        fail(
            "data/opportunities.json changed unexpectedly "
            "during frontend integration."
        )

    if len(web_after) != EXPECTED_COUNT:
        fail(
            "web/opportunities.json changed unexpectedly "
            "during frontend integration."
        )

    print(
        "PASS: both backend and frontend datasets still contain "
        f"{EXPECTED_COUNT} opportunities."
    )

    if REPAIR_CHECKPOINT.exists():
        checkpoint_after = sha256(REPAIR_CHECKPOINT)

        if checkpoint_after != checkpoint_hash:
            fail("Repair checkpoint changed during frontend integration.")

    after_app = APP_JS.read_text(encoding="utf-8")

    after_provider = DATA_PROVIDER_JS.read_text(encoding="utf-8")

    after_index = INDEX_HTML.read_text(encoding="utf-8")

    write_review(
        before_app=before_app,
        before_provider=before_provider,
        before_index=before_index,
        after_app=after_app,
        after_provider=after_provider,
        after_index=after_index,
        participant_country_sample=participant_country_sample,
        participant_country_sample_count=participant_country_sample_count,
    )

    # The checkpoint must remain local-only.
    if REPAIR_CHECKPOINT.exists():
        print("PASS: repair checkpoint remains local and uncommitted.")

    print()
    print("=" * 72)
    print("PRE-COMMIT VALIDATION")
    print("=" * 72)

    node_check(APP_JS)
    node_check(DATA_PROVIDER_JS)

    validate_provider_source()
    validate_app_source()
    validate_country_selector()
    validate_1178_dataset()
    validate_checkpoint()

    stage_allowed_files()
    commit_changes()
    push_main()

    verify_final_state()

    print()
    print("=" * 72)
    print("DONE")
    print("=" * 72)
    print()
    print(
        "The full 1,178-opportunity dataset is now connected "
        "to the GitHub Pages frontend."
    )
    print()
    print(
        "The frontend provider loads web/opportunities.json, "
        "splits active/recently expired opportunities, and "
        "supports participant-country eligibility filtering."
    )
    print()
    print("The full-detail repair checkpoint remains local-only.")


if __name__ == "__main__":
    main()
