#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

APP_FILE = ROOT / "web" / "app.js"
INDEX_HTML_FILE = ROOT / "web" / "index.html"

CANONICAL_CACHE = ROOT / "data" / "opportunities.json"
PUBLISHED_CACHE = ROOT / "web" / "opportunities.json"

PARTICIPANT_INDEX = ROOT / "data" / "participant_country_index.json"
PUBLISHED_PARTICIPANT_INDEX = ROOT / "web" / "participant_country_index.json"

SCRAPER_FILE = ROOT / "scraper" / "scraper.py"

MANAGED_FILES = [
    "web/app.js",
    "web/index.html",
    "update.py",
]

REQUIRED_FILES = [
    "scraper/scraper.py",
    "data/opportunities.json",
    "data/participant_country_index.json",
    "web/opportunities.json",
    "web/participant_country_index.json",
    "web/app.js",
    "web/index.html",
]

PARTICIPANT_SECTION_START = (
    "// ============================================================\n"
    "// PARTICIPANT COUNTRY FILTER\n"
    "// ============================================================\n"
)

FILTER_OPTIONS_SECTION = (
    "// ============================================================\n"
    "// FILTER OPTIONS\n"
    "// ============================================================\n"
)

FILTERING_SECTION = (
    "// ============================================================\n"
    "// FILTERING\n"
    "// ============================================================\n"
)

SORTING_SECTION = (
    "// ============================================================\n"
    "// SORTING\n"
    "// ============================================================\n"
)

REFRESH_BUTTON_SECTION = (
    "// ============================================================\n"
    "// REFRESH BUTTON\n"
    "// ============================================================\n"
)

PHASE_TWO_SECTION = (
    "// ============================================================\n"
    "// PHASE TWO CACHE-FIRST SEARCH INTEGRATION\n"
    "// ============================================================\n"
)


def banner(text):
    print()
    print("=" * 72)
    print(text)
    print("=" * 72)


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


def write_text(path, content):
    path.write_text(
        content.rstrip("\r\n") + "\n",
        encoding="utf-8",
    )


def load_json(path):
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc


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
        print(status, end="" if status.endswith("\n") else "\n")
        print(
            "NOTE: Existing changes detected; only Phase Five files " "will be staged."
        )
        print("NOTE: Unrelated changes will remain untouched.")
    else:
        print("PASS: working tree is clean.")


def check_branch():
    print("\nChecking branch...")

    result = run(
        ["git", "branch", "--show-current"],
        capture=True,
    )

    branch = result.stdout.strip()

    if branch != "main":
        raise RuntimeError(f"Expected branch main, found {branch!r}.")

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

    parts = result.stdout.strip().split()

    if len(parts) != 2:
        raise RuntimeError("Could not determine local/remote commit state.")

    local_only = int(parts[0])
    remote_only = int(parts[1])

    print(f"Local-only commits: {local_only}")
    print(f"Remote-only commits: {remote_only}")

    if local_only != 0:
        raise RuntimeError("Local main contains commits not present remotely.")

    if remote_only != 0:
        raise RuntimeError("Remote main contains commits not present locally.")

    print("PASS: local main is synchronized with origin/main.")


def validate_scraper():
    print("\nValidating existing scraper architecture...")

    source = read_text(SCRAPER_FILE)

    required = [
        "eligible_countries",
        "eligibility_known",
        "CHECKPOINT_FILE",
        "OPPORTUNITIES_FILE",
        "BATCH_SIZE",
        "DETAIL_REQUEST_DELAY",
        "MAX_RETRIES",
    ]

    missing = [marker for marker in required if marker not in source]

    if missing:
        raise RuntimeError(
            "Scraper architecture validation failed:\n"
            + "\n".join(f"  - {item}" for item in missing)
        )

    print(
        "PASS: existing resumable/incremental "
        "country-agnostic scraper architecture remains intact."
    )


def validate_workflow():
    print("\nValidating hourly scraper workflow...")

    candidates = [
        ROOT / ".github" / "workflows" / "update.yml",
        ROOT / ".github" / "workflows" / "scrape.yml",
    ]

    workflow = next(
        (path for path in candidates if path.is_file()),
        None,
    )

    if workflow is None:
        raise RuntimeError("No hourly scraper workflow found.")

    source = read_text(workflow)

    if "schedule:" not in source or "cron:" not in source:
        raise RuntimeError("Hourly scraper workflow is missing its schedule.")

    print(
        f"PASS: hourly scraper workflow is present " f"({workflow.relative_to(ROOT)})."
    )


def validate_cache():
    print("\nValidating canonical and published caches...")

    canonical = load_json(CANONICAL_CACHE)
    published = load_json(PUBLISHED_CACHE)

    canonical_ops = canonical.get("opportunities")
    published_ops = published.get("opportunities")

    if not isinstance(canonical_ops, list):
        raise RuntimeError("Canonical cache does not contain an opportunities list.")

    if not isinstance(published_ops, list):
        raise RuntimeError("Published cache does not contain an opportunities list.")

    if not canonical_ops:
        raise RuntimeError("Canonical opportunity cache is empty.")

    canonical_by_id = {
        str(item.get("id")): item
        for item in canonical_ops
        if isinstance(item, dict) and item.get("id") is not None
    }

    published_by_id = {
        str(item.get("id")): item
        for item in published_ops
        if isinstance(item, dict) and item.get("id") is not None
    }

    if len(canonical_by_id) != len(canonical_ops):
        raise RuntimeError("Canonical cache contains duplicate opportunity IDs.")

    if set(canonical_by_id) != set(published_by_id):
        raise RuntimeError(
            "Canonical and published caches contain different " "opportunity IDs."
        )

    for opportunity_id in canonical_by_id:
        canonical_item = canonical_by_id[opportunity_id]
        published_item = published_by_id[opportunity_id]

        if canonical_item.get("eligible_countries") != published_item.get(
            "eligible_countries"
        ):
            raise RuntimeError(
                f"Published cache differs from canonical cache "
                f"for opportunity {opportunity_id}."
            )

    with_country_data = sum(
        isinstance(item.get("eligible_countries"), list)
        for item in canonical_ops
        if isinstance(item, dict)
    )

    print(f"Canonical opportunities: {len(canonical_ops)}")
    print(f"Published opportunities: {len(published_ops)}")
    print("Opportunities with participant-country data: " f"{with_country_data}")

    if with_country_data != len(canonical_ops):
        raise RuntimeError(
            "Not every canonical opportunity has participant-country data."
        )

    print("PASS: canonical and published caches are consistent.")

    return canonical


def validate_index(canonical):
    print("\nValidating participant-country index...")

    index = load_json(PARTICIPANT_INDEX)

    if index.get("schema_version") != 1:
        raise RuntimeError("Unsupported participant-country index schema.")

    countries = index.get("countries")

    if not isinstance(countries, dict):
        raise RuntimeError("Participant-country index has an invalid countries object.")

    canonical_by_id = {
        str(item["id"]): item
        for item in canonical["opportunities"]
        if isinstance(item, dict) and item.get("id") is not None
    }

    expected = {}

    for opportunity in canonical["opportunities"]:
        if not isinstance(opportunity, dict):
            continue

        opportunity_id = str(opportunity["id"])

        eligible = opportunity.get(
            "eligible_countries",
            [],
        )

        if not isinstance(eligible, list):
            raise RuntimeError(
                f"Opportunity {opportunity_id} has invalid " "eligible_countries."
            )

        for country in eligible:
            if not isinstance(country, str):
                continue

            code = country.strip().upper()

            if not code:
                continue

            expected.setdefault(code, set()).add(opportunity_id)

    actual = {}

    for country_code, opportunity_ids in countries.items():
        normalized_code = str(country_code).strip().upper()

        if not isinstance(opportunity_ids, list):
            raise RuntimeError(f"Index entry {normalized_code} is not a list.")

        actual[normalized_code] = {str(value) for value in opportunity_ids}

    if set(expected) != set(actual):
        raise RuntimeError(
            "Participant-country index country set differs from "
            "canonical eligibility data."
        )

    for code in expected:
        if expected[code] != actual[code]:
            raise RuntimeError(f"Participant-country index mismatch for {code}.")

        for opportunity_id in actual[code]:
            if opportunity_id not in canonical_by_id:
                raise RuntimeError(
                    f"Index {code} references unknown " f"opportunity {opportunity_id}."
                )

    morocco_count = len(actual.get("MA", set()))

    if morocco_count == 0:
        raise RuntimeError("Morocco (MA) has no indexed opportunities.")

    if len(actual) < 2:
        raise RuntimeError("Participant-country index is not country-agnostic.")

    print(f"Indexed participant countries: {len(actual)}")
    print(f"Indexed opportunities: {len(canonical_by_id)}")
    print(f"Morocco (MA) indexed opportunities: {morocco_count}")
    print(
        "PASS: participant-country index exactly matches " "canonical eligibility data."
    )

    published_index = load_json(PUBLISHED_PARTICIPANT_INDEX)

    if published_index != index:
        raise RuntimeError(
            "data/participant_country_index.json and "
            "web/participant_country_index.json differ."
        )

    print("PASS: published participant-country index is synchronized.")

    return index


def remove_all_index_url_declarations(source):
    """
    Make the transformation idempotent.

    Previous failed attempts may already have inserted the same
    const declaration one or more times. Remove every declaration
    before inserting exactly one canonical declaration.
    """

    pattern = re.compile(
        r"^[ \t]*const\s+PARTICIPANT_COUNTRY_INDEX_URL\s*=\s*"
        r'"participant_country_index\.json";[ \t]*\n?',
        re.MULTILINE,
    )

    updated, count = pattern.subn(
        "",
        source,
    )

    if count:
        print(
            f"Removed {count} existing " "PARTICIPANT_COUNTRY_INDEX_URL declaration(s)."
        )

    marker = 'const EXPIRED_DATA_URL = "expired.json";'

    if marker not in updated:
        raise RuntimeError("Could not locate EXPIRED_DATA_URL.")

    replacement = (
        marker + "\n" + "const PARTICIPANT_COUNTRY_INDEX_URL = "
        '"participant_country_index.json";'
    )

    updated = updated.replace(
        marker,
        replacement,
        1,
    )

    return updated


def remove_all_index_state_declarations(source):
    pattern = re.compile(
        r"^[ \t]*let\s+participantCountryIndex\s*=\s*null;[ \t]*\n?",
        re.MULTILINE,
    )

    updated, count = pattern.subn(
        "",
        source,
    )

    if count:
        print(f"Removed {count} existing " "participantCountryIndex declaration(s).")

    marker = "let currentActiveData = null;"

    if marker not in updated:
        raise RuntimeError("Could not locate currentActiveData declaration.")

    updated = updated.replace(
        marker,
        marker + "\n" + "let participantCountryIndex = null;",
        1,
    )

    return updated


def replace_section(
    source,
    start_marker,
    end_marker,
    replacement,
):
    start = source.find(start_marker)

    if start == -1:
        raise RuntimeError(
            f"Could not locate section start: "
            f"{start_marker.splitlines()[1] if start_marker.splitlines() else start_marker}"
        )

    end = source.find(
        end_marker,
        start + len(start_marker),
    )

    if end == -1:
        raise RuntimeError(f"Could not locate section end.")

    return source[:start] + replacement.rstrip() + "\n" + source[end:]


def replace_participant_country_section(source):
    participant_section = (
        r"""// ============================================================
// PARTICIPANT COUNTRY FILTER
// ============================================================

const PARTICIPANT_COUNTRY_STORAGE_KEY =
  "esc_participant_country";

const participantCountryFilter =
  document.getElementById(
    "participant-country",
  );

const applyParticipantCountryButton =
  document.getElementById(
    "apply-participant-country",
  );

let selectedParticipantCountry = "";
let participantCountryDraft = "";
let participantSearchApplied = false;

function normalizeParticipantCountry(value) {
  return String(value || "")
    .trim()
    .replace(/\s+/g, " ")
    .toLocaleLowerCase();
}

function getParticipantCountryCode(name) {
  const normalizedName =
    normalizeParticipantCountry(name);

  const country =
    ESC_PARTICIPANT_COUNTRIES.find(
      (item) =>
        normalizeParticipantCountry(
          item.name,
        ) === normalizedName,
    );

  if (!country) {
    return "";
  }

  const regionalIndicators =
    [...country.flag]
      .map((character) =>
        character.codePointAt(0),
      )
      .filter(
        (codePoint) =>
          codePoint >= 0x1f1e6 &&
          codePoint <= 0x1f1ff,
      );

  if (
    regionalIndicators.length !== 2
  ) {
    return "";
  }

  return regionalIndicators
    .map(
      (codePoint) =>
        String.fromCharCode(
          codePoint - 0x1f1e6 + 65,
        ),
    )
    .join("");
}

function getParticipantCountryOpportunityIds() {
  if (!selectedParticipantCountry) {
    return null;
  }

  if (
    !participantCountryIndex ||
    typeof participantCountryIndex.countries !==
      "object"
  ) {
    return new Set();
  }

  const countryCode =
    getParticipantCountryCode(
      selectedParticipantCountry,
    );

  if (!countryCode) {
    return new Set();
  }

  const ids =
    participantCountryIndex.countries[
      countryCode
    ];

  if (!Array.isArray(ids)) {
    return new Set();
  }

  return new Set(
    ids.map((id) =>
      String(id),
    ),
  );
}

async function ensureParticipantCountryIndex() {
  if (
    participantCountryIndex &&
    typeof participantCountryIndex.countries ===
      "object"
  ) {
    return participantCountryIndex;
  }

  const data = await fetchJson(
    PARTICIPANT_COUNTRY_INDEX_URL,
  );

  if (
    !data ||
    typeof data !== "object" ||
    !data.countries ||
    typeof data.countries !== "object"
  ) {
    throw new Error(
      "Participant-country index has an invalid structure.",
    );
  }

  participantCountryIndex = data;

  return participantCountryIndex;
}

function populateParticipantCountries() {
  if (!participantCountryFilter) {
    return;
  }

  const currentValue =
    participantCountryFilter.value;

  participantCountryFilter.innerHTML = "";

  const placeholder =
    document.createElement("option");

  placeholder.value = "";
  placeholder.textContent =
    t("selectParticipantCountry");

  participantCountryFilter.appendChild(
    placeholder,
  );

  ESC_PARTICIPANT_COUNTRIES.forEach(
    (country) => {
      const option =
        document.createElement("option");

      option.value =
        country.name;

      option.textContent =
        `${country.flag} ${country.name}`;

      participantCountryFilter.appendChild(
        option,
      );
    },
  );

  const exists =
    [...participantCountryFilter.options]
      .some(
        (option) =>
          option.value === currentValue,
      );

  participantCountryFilter.value =
    exists ? currentValue : "";
}

async function applyParticipantCountry() {
  if (!participantCountryFilter) {
    return;
  }

  selectedParticipantCountry =
    participantCountryFilter.value.trim();

  participantCountryDraft =
    selectedParticipantCountry;

  participantSearchApplied =
    Boolean(
      selectedParticipantCountry,
    );

  if (!participantSearchApplied) {
    resetParticipantSearchDisplay();
    return;
  }

  loadingMessage.classList.remove(
    "hidden",
  );

  errorMessage.classList.add(
    "hidden",
  );

  try {
    await ensureParticipantCountryIndex();

    renderActive();
    updateHeaderForParticipantSearch();
  } catch (error) {
    console.error(
      "Could not load participant-country index:",
      error,
    );

    opportunitiesBody.innerHTML = "";

    opportunityCount.textContent = "—";
    activeResultCount.textContent = "—";
    lastUpdated.textContent = "—";

    emptyMessage.classList.add("hidden");
    errorMessage.classList.remove("hidden");
  } finally {
    loadingMessage.classList.add(
      "hidden",
    );
  }
}

if (participantCountryFilter) {
  participantCountryFilter.addEventListener(
    "change",
    () => {
      participantCountryDraft =
        participantCountryFilter.value;
    },
  );
}

if (applyParticipantCountryButton) {
  applyParticipantCountryButton.addEventListener(
    "click",
    applyParticipantCountry,
  );
}
""".strip()
    )

    return replace_section(
        source,
        PARTICIPANT_SECTION_START,
        FILTER_OPTIONS_SECTION,
        participant_section,
    )


def replace_get_filtered_active(source):
    pattern = re.compile(
        r"function getFilteredActive\(\)\s*\{.*?"
        r"(?=^// ============================================================\n"
        r"// SORTING\n"
        r"// ============================================================\n)",
        re.MULTILINE | re.DOTALL,
    )

    replacement = r"""function getFilteredActive() {
  const search =
    searchInput.value
      .trim()
      .toLowerCase();

  const country =
    countryFilter.value;

  const type =
    typeFilter.value;

  const participantOpportunityIds =
    getParticipantCountryOpportunityIds();

  return activeOpportunities.filter(
    (opportunity) => {
      const searchable = [
        opportunity.title,
        opportunity.location,
        opportunity.town,
        getCountryName(
          opportunity.country,
        ),
        opportunity.activity_type,
        ...(opportunity.topics || []),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      if (
        search &&
        !searchable.includes(search)
      ) {
        return false;
      }

      if (
        country &&
        opportunity.country !== country
      ) {
        return false;
      }

      if (
        participantOpportunityIds !==
          null &&
        !participantOpportunityIds.has(
          String(opportunity.id),
        )
      ) {
        return false;
      }

      if (
        type &&
        opportunity.activity_type !==
          type
      ) {
        return false;
      }

      return true;
    },
  );
}
// ============================================================
// SORTING
// ============================================================
"""

    updated, count = pattern.subn(
        replacement,
        source,
        count=1,
    )

    if count != 1:
        raise RuntimeError("Could not safely replace getFilteredActive().")

    return updated


def replace_load_data(source):
    pattern = re.compile(
        r"async function loadData\(\)\s*\{.*?"
        r"(?=^// ============================================================\n"
        r"// REFRESH BUTTON\n"
        r"// ============================================================\n)",
        re.MULTILINE | re.DOTALL,
    )

    replacement = r"""async function loadData() {
  loadingMessage.classList.remove(
    "hidden",
  );

  errorMessage.classList.add(
    "hidden",
  );

  try {
    const [
      activeData,
      indexData,
    ] = await Promise.all([
      fetchJson(DATA_URL),
      fetchJson(
        PARTICIPANT_COUNTRY_INDEX_URL,
      ),
    ]);

    if (
      !activeData ||
      !Array.isArray(
        activeData.opportunities,
      )
    ) {
      throw new Error(
        "Published opportunity cache has an invalid structure.",
      );
    }

    if (
      !indexData ||
      typeof indexData !== "object" ||
      !indexData.countries ||
      typeof indexData.countries !==
        "object"
    ) {
      throw new Error(
        "Participant-country index has an invalid structure.",
      );
    }

    currentActiveData =
      activeData;

    activeOpportunities =
      activeData.opportunities;

    participantCountryIndex =
      indexData;

    calculateNewOpportunities(
      activeOpportunities,
    );

    try {
      const expiredData =
        await fetchJson(
          EXPIRED_DATA_URL,
        );

      expiredOpportunities =
        Array.isArray(
          expiredData?.opportunities,
        )
          ? expiredData.opportunities
          : [];
    } catch {
      expiredOpportunities = [];
    }

    populateFilters();
    populateParticipantCountries();

    resetParticipantSearchDisplay();

    renderExpired();
  } catch (error) {
    console.error(
      "Could not load opportunities:",
      error,
    );

    activeOpportunities = [];
    currentActiveData = null;
    participantCountryIndex = null;

    opportunityCount.textContent = "—";
    activeResultCount.textContent = "—";
    lastUpdated.textContent = "—";

    errorMessage.classList.remove(
      "hidden",
    );
  } finally {
    loadingMessage.classList.add(
      "hidden",
    );
  }
}

// ============================================================
// REFRESH BUTTON
// ============================================================
"""

    updated, count = pattern.subn(
        replacement,
        source,
        count=1,
    )

    if count != 1:
        raise RuntimeError("Could not safely replace loadData().")

    return updated


def remove_phase_two_tail(source):
    start = source.find(
        PHASE_TWO_SECTION,
    )

    if start == -1:
        print("No obsolete Phase Two tail found.")
        return source

    print("Removing obsolete Phase Two frontend tail.")

    return source[:start].rstrip() + "\n"


def update_frontend():
    print("\nUpdating frontend participant-country index integration...")

    app = read_text(
        APP_FILE,
    )

    # This is the critical idempotency repair. Previous failed updater
    # executions may have inserted this declaration already, so never
    # blindly append another one.
    app = remove_all_index_url_declarations(
        app,
    )

    app = remove_all_index_state_declarations(
        app,
    )

    app = replace_participant_country_section(
        app,
    )

    app = replace_get_filtered_active(
        app,
    )

    app = replace_load_data(
        app,
    )

    app = remove_phase_two_tail(
        app,
    )

    # Add a single descriptive Phase Five marker before INITIAL LOAD.
    initial_load_marker = (
        "// ============================================================\n"
        "// INITIAL LOAD\n"
        "// ============================================================\n"
    )

    if "PHASE FIVE — PARTICIPANT-COUNTRY INDEX" not in app:
        if initial_load_marker not in app:
            raise RuntimeError("Could not locate INITIAL LOAD section.")

        phase_five_note = """// ============================================================
// PHASE FIVE — PARTICIPANT-COUNTRY INDEX
// ============================================================
//
// The frontend reads the published country index and canonical
// opportunity cache directly from GitHub Pages.
//
// Participant countries are represented by country codes.
// No country, including Morocco, is hard-coded as a special case.
// ============================================================

"""

        app = app.replace(
            initial_load_marker,
            phase_five_note + initial_load_marker,
            1,
        )

    write_text(
        APP_FILE,
        app,
    )

    print(
        "PASS: frontend participant-country filtering "
        "now uses the published country index."
    )


def bump_cache_version():
    print("\nUpdating frontend cache-busting...")

    html = read_text(
        INDEX_HTML_FILE,
    )

    matches = re.findall(
        r"app\.js\?v=(\d+)",
        html,
    )

    if len(matches) != 1:
        raise RuntimeError(
            "Expected exactly one app.js cache-busting " "version in web/index.html."
        )

    current = int(matches[0])
    new_version = current + 1

    updated = re.sub(
        r"app\.js\?v=\d+",
        f"app.js?v={new_version}",
        html,
        count=1,
    )

    write_text(
        INDEX_HTML_FILE,
        updated,
    )

    print(f"PASS: app.js cache version bumped " f"v{current} -> v{new_version}.")


def normalize_frontend_eof():
    print("\nNormalizing frontend file endings...")

    for path in [
        APP_FILE,
        INDEX_HTML_FILE,
    ]:
        content = read_text(path)

        normalized = content.rstrip("\r\n") + "\n"

        if content != normalized:
            write_text(
                path,
                normalized,
            )

            print(f"PASS: normalized " f"{path.relative_to(ROOT)}.")
        else:
            print(f"PASS: " f"{path.relative_to(ROOT)} already has a clean EOF.")


def validate_frontend_contract():
    print("\nValidating frontend integration...")

    html = read_text(
        INDEX_HTML_FILE,
    )

    app = read_text(
        APP_FILE,
    )

    required_html = [
        'id="participant-country"',
        'id="apply-participant-country"',
        "app.js?v=",
    ]

    missing_html = [marker for marker in required_html if marker not in html]

    if missing_html:
        raise RuntimeError(
            "Frontend HTML contract failed:\n"
            + "\n".join(f"  - {item}" for item in missing_html)
        )

    required_app = [
        "const PARTICIPANT_COUNTRY_INDEX_URL = " '"participant_country_index.json";',
        "let participantCountryIndex = null;",
        "async function ensureParticipantCountryIndex()",
        "fetchJson(\n    PARTICIPANT_COUNTRY_INDEX_URL,",
        "getParticipantCountryOpportunityIds",
        "participantCountryIndex.countries",
        "participantOpportunityIds",
        "async function applyParticipantCountry()",
        "async function loadData()",
    ]

    missing_app = [marker for marker in required_app if marker not in app]

    if missing_app:
        raise RuntimeError(
            "Frontend JavaScript contract failed:\n"
            + "\n".join(f"  - {item}" for item in missing_app)
        )

    declaration_count = len(
        re.findall(
            r"const\s+PARTICIPANT_COUNTRY_INDEX_URL\s*=\s*"
            r'"participant_country_index\.json";',
            app,
        )
    )

    if declaration_count != 1:
        raise RuntimeError(
            "Expected exactly one "
            "PARTICIPANT_COUNTRY_INDEX_URL declaration; "
            f"found {declaration_count}."
        )

    state_count = len(
        re.findall(
            r"let\s+participantCountryIndex\s*=\s*null;",
            app,
        )
    )

    if state_count != 1:
        raise RuntimeError(
            "Expected exactly one participantCountryIndex state "
            f"declaration; found {state_count}."
        )

    forbidden = [
        "PHASE_TWO_PARTICIPANT_COUNTRIES",
        "phaseTwoCountryCodeFromName",
        "phaseTwoLoadParticipantCountryResults",
        "phaseTwoHandleParticipantCountrySearch",
        "phaseTwoInstallParticipantCountrySearch",
        'selectedNormalized !== "morocco"',
        'normalizeParticipantCountry("Morocco")',
        "backend currently contains cached",
        "country-specific backend scraping",
        "Backend support is currently Morocco-only.",
    ]

    stale = [marker for marker in forbidden if marker in app]

    if stale:
        raise RuntimeError(
            "Obsolete Morocco-only/Phase Two frontend logic remains:\n"
            + "\n".join(f"  - {item}" for item in stale)
        )

    print(
        "PASS: frontend is country-agnostic "
        "and uses the published participant-country index."
    )


def validate_frontend_index_relationship():
    print("\nValidating frontend index/cache relationship...")

    index = load_json(
        PUBLISHED_PARTICIPANT_INDEX,
    )

    cache = load_json(
        PUBLISHED_CACHE,
    )

    opportunities = cache.get(
        "opportunities",
        [],
    )

    opportunity_ids = {
        str(item["id"])
        for item in opportunities
        if isinstance(item, dict) and item.get("id") is not None
    }

    countries = index.get(
        "countries",
        {},
    )

    total_ma = len(countries.get("MA", []))

    if total_ma == 0:
        raise RuntimeError("Published frontend index contains no MA results.")

    for country, ids in countries.items():
        if not isinstance(ids, list):
            raise RuntimeError(f"Published index entry {country} is not a list.")

        for opportunity_id in ids:
            if str(opportunity_id) not in opportunity_ids:
                raise RuntimeError(
                    f"Published index {country} references unknown "
                    f"opportunity {opportunity_id}."
                )

    print(f"Morocco frontend results: {total_ma}")
    print(f"Published opportunities: " f"{len(opportunity_ids)}")
    print(
        "PASS: every published participant-country index ID "
        "resolves to a published opportunity."
    )


def run_node_check():
    print("\nRunning JavaScript syntax validation...")

    run(
        [
            "node",
            "--check",
            "web/app.js",
        ]
    )

    print("PASS: web/app.js syntax is valid.")


def run_python_check():
    print("\nRunning Python syntax validation...")

    run(
        [
            sys.executable,
            "-m",
            "py_compile",
            "scraper/scraper.py",
            "backend/cache.py",
            "backend/search.py",
            "backend/test_search.py",
            "update.py",
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

    print("PASS: backend tests passed.")


def validate_backend_ma():
    print("\nValidating Morocco backend search...")

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
        raise RuntimeError("backend.search MA returned invalid JSON.") from exc

    if payload.get("status") != "success":
        raise RuntimeError("backend.search MA did not return success.")

    if payload.get("participant_country") != "MA":
        raise RuntimeError("backend.search MA returned the wrong country.")

    count = payload.get("count")

    if not isinstance(count, int) or count <= 0:
        raise RuntimeError("backend.search MA returned zero opportunities.")

    print(f"Morocco backend results: {count}")

    print("PASS: backend indexed Morocco search remains operational.")


def git_whitespace_check():
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
    print("\nPreparing selective Phase Five commit...")

    run(
        [
            "git",
            "reset",
        ]
    )

    for relative in MANAGED_FILES:
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

    unexpected = sorted(set(staged) - set(MANAGED_FILES))

    if unexpected:
        raise RuntimeError(
            "Unexpected files are staged:\n"
            + "\n".join(f"  - {item}" for item in unexpected)
        )

    if not staged:
        raise RuntimeError("No Phase Five changes are staged.")

    print("Files staged for Phase Five:")

    for path in staged:
        print(f"  {path}")

    run(
        [
            "git",
            "diff",
            "--cached",
            "--stat",
        ]
    )

    print("\nCreating Phase Five commit...")

    run(
        [
            "git",
            "commit",
            "-m",
            "feat: connect frontend to participant-country index",
        ]
    )

    print("\nPushing Phase Five commit...")

    run(
        [
            "git",
            "push",
            "origin",
            "main",
        ]
    )

    print("\nPASS: Phase Five commit pushed successfully.")


def main():
    banner("ESC Opportunity Finder — " "Phase Five frontend participant-country index")

    print("""This update will:
  - preserve the background scraper and hourly workflow
  - preserve the canonical opportunity cache
  - validate the participant-country index
  - repair previous partial Phase Five edits idempotently
  - remove duplicate index declarations
  - remove obsolete Morocco-only frontend logic
  - load participant_country_index.json from GitHub Pages
  - resolve selected countries to indexed opportunity IDs
  - keep opportunity objects sourced from opportunities.json
  - preserve the participant-country selector UI
  - bump frontend cache-busting
  - validate JavaScript with node --check
  - validate Python/backend/cache/index consistency
  - selectively commit and push only Phase Five files
""")

    try:
        require_files()
        check_git_state()
        check_branch()
        check_remote()

        validate_scraper()
        validate_workflow()

        canonical = validate_cache()
        validate_index(canonical)

        update_frontend()
        bump_cache_version()
        normalize_frontend_eof()

        validate_frontend_contract()
        validate_frontend_index_relationship()

        run_node_check()
        run_python_check()
        run_backend_tests()
        validate_backend_ma()

        git_whitespace_check()

        selective_commit_and_push()

        banner("PHASE FIVE COMPLETE")

        print(
            "The frontend now uses the country-agnostic " "participant-country index."
        )

    except Exception as exc:
        banner("UPDATE FAILED")

        print(str(exc))
        print()
        print("No Phase Five commit or push was performed.")

        sys.exit(1)


if __name__ == "__main__":
    main()
