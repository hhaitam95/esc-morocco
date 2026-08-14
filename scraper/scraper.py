import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "https://youth.europa.eu"
API_URL = f"{BASE_URL}/api/rest/eyp/v1/search_en"

TARGET_COUNTRY = "Morocco"

# ------------------------------------------------------------
# API
# ------------------------------------------------------------

API_PAGE_SIZE = 100

# ------------------------------------------------------------
# Detail-page scanning
# ------------------------------------------------------------

# Number of detail pages processed by ONE scraper invocation.
#
# Your GitHub workflow currently runs several invocations per
# workflow. Keeping this small makes each individual batch safe.
BATCH_SIZE = 40

# Delay between detail-page requests.
DETAIL_REQUEST_DELAY = 5.0

# Cooldown before starting the detail scan.
DETAIL_SCAN_COOLDOWN = 10.0

# Hard timeout for individual HTTP requests.
REQUEST_TIMEOUT = 20

# Maximum retries for temporary failures.
MAX_RETRIES = 3

# Maximum number of seconds to respect for Retry-After.
MAX_RATE_LIMIT_WAIT = 120

# Number of archived opportunities kept in expired.json.
MAX_ARCHIVED_OPPORTUNITIES = 30


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"

CHECKPOINT_FILE = DATA_DIR / "checkpoint.json"
OPPORTUNITIES_FILE = DATA_DIR / "opportunities.json"
EXPIRED_FILE = DATA_DIR / "expired.json"

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# DATES
# ============================================================

TODAY = datetime.now().replace(
    hour=0,
    minute=0,
    second=0,
    microsecond=0,
)

TODAY_API = TODAY.strftime("%Y-%m-%dT00:00:00")


# ============================================================
# HTTP HEADERS
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
}


# ============================================================
# API PARAMETERS
# ============================================================


def build_api_params(offset: int) -> dict:
    """
    Build the same search query used by the European Youth Portal.
    """

    return {
        "type": "Opportunity",
        "size": API_PAGE_SIZE,
        "from": offset,
        # Open opportunities.
        "filters[status]": "open",
        # Activity has not ended.
        "filters[date_end][operator]": ">=",
        "filters[date_end][value]": TODAY_API,
        "filters[date_end][type]": "must",
        # Funding programmes used by the portal.
        "filters[funding_programme][id][0]": 5,
        "filters[funding_programme][id][1]": 4,
        "filters[funding_programme][id][2]": 3,
        "filters[funding_programme][id][3]": 2,
        "filters[funding_programme][id][4]": 1,
        "filters[funding_programme][id][5]": 8,
        "filters[funding_programme][id][6]": 6,
        "filters[funding_programme][id][7]": 7,
        # Application deadline is still valid.
        "filters[date_application_end][operator]": ">=",
        "filters[date_application_end][value]": TODAY_API,
        "filters[date_application_end][type]": "must",
        "filters[date_application_end][group]": "deadline",
        # Include opportunities without a deadline.
        "filters[has_no_deadline][value]": "true",
        "filters[has_no_deadline][type]": "must",
        "filters[has_no_deadline][group]": "deadline",
        # Fields.
        "fields[0]": "opid",
        "fields[1]": "title",
        "fields[2]": "town",
        "fields[3]": "country",
        "fields[4]": "date_start",
        "fields[5]": "date_end",
        "fields[6]": "date_application_end",
        "fields[7]": "has_no_deadline",
        "fields[8]": "duration",
        "fields[9]": "created",
        "fields[10]": "is_esc_related",
        # Newest first.
        "sort[created]": "desc",
    }


# ============================================================
# GENERIC HELPERS
# ============================================================


def now_iso() -> str:
    return datetime.now().isoformat()


def atomic_write_json(
    path: Path,
    data: dict,
) -> None:
    """
    Write JSON atomically so an interrupted write does not leave
    a half-written file.
    """

    temporary = path.with_suffix(".tmp")

    with temporary.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    temporary.replace(path)


def parse_iso_datetime(
    value: str | None,
) -> datetime | None:

    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


# ============================================================
# CHECKPOINT
# ============================================================


def load_checkpoint() -> dict:

    if not CHECKPOINT_FILE.exists():
        return {
            "processed": {},
            "history": {},
            "last_scan_at": None,
        }

    try:

        with CHECKPOINT_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        if not isinstance(
            data,
            dict,
        ):
            raise ValueError("Checkpoint is not a JSON object.")

        if not isinstance(
            data.get("processed"),
            dict,
        ):
            data["processed"] = {}

        if not isinstance(
            data.get("history"),
            dict,
        ):
            data["history"] = {}

        data.setdefault(
            "last_scan_at",
            None,
        )

        return data

    except (
        OSError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:

        print(
            f"Could not read checkpoint: {exc}",
            flush=True,
        )

        return {
            "processed": {},
            "history": {},
            "last_scan_at": None,
        }


def save_checkpoint(
    checkpoint: dict,
) -> None:

    checkpoint["last_scan_at"] = now_iso()
    checkpoint["updated_at"] = now_iso()

    atomic_write_json(
        CHECKPOINT_FILE,
        checkpoint,
    )


# ============================================================
# API FETCHING
# ============================================================


def get_retry_after_seconds(
    response: requests.Response,
) -> int:
    """
    Respect Retry-After when the server provides it.
    Otherwise use a conservative default.
    """

    value = response.headers.get("Retry-After")

    if value:

        try:

            seconds = int(float(value))

            return max(
                1,
                min(
                    seconds,
                    MAX_RATE_LIMIT_WAIT,
                ),
            )

        except ValueError:
            pass

    return 30


def fetch_api_page(
    session: requests.Session,
    offset: int,
) -> dict | None:

    params = build_api_params(offset)

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        try:

            print(
                f"API request: " f"from={offset}, " f"size={API_PAGE_SIZE}",
                flush=True,
            )

            response = session.get(
                API_URL,
                params=params,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code == 200:

                return response.json()

            if response.status_code == 429:

                wait = get_retry_after_seconds(response)

                print(
                    f"API HTTP 429. "
                    f"Waiting {wait}s before retry "
                    f"({attempt}/{MAX_RETRIES})...",
                    flush=True,
                )

                if attempt >= MAX_RETRIES:

                    return None

                time.sleep(wait)

                continue

            if response.status_code >= 500:

                if attempt < MAX_RETRIES:

                    wait = 2**attempt

                    print(
                        f"API HTTP "
                        f"{response.status_code}. "
                        f"Retrying in {wait}s...",
                        flush=True,
                    )

                    time.sleep(wait)

                    continue

                return None

            print(
                f"API error: " f"HTTP {response.status_code}",
                flush=True,
            )

            return None

        except requests.Timeout:

            if attempt < MAX_RETRIES:

                wait = 2**attempt

                print(
                    f"API timeout. " f"Retrying in {wait}s...",
                    flush=True,
                )

                time.sleep(wait)

                continue

            return None

        except requests.RequestException as exc:

            if attempt < MAX_RETRIES:

                wait = 2**attempt

                print(
                    f"API request error: {exc}",
                    flush=True,
                )

                print(
                    f"Retrying in {wait}s...",
                    flush=True,
                )

                time.sleep(wait)

                continue

            print(
                f"API request failed: {exc}",
                flush=True,
            )

            return None

    return None


def fetch_current_opportunities() -> list[dict]:

    print("=" * 70)
    print("FETCHING CURRENT OPPORTUNITIES")
    print("=" * 70)

    session = requests.Session()

    opportunities = []

    offset = 0
    total = None

    try:

        while True:

            data = fetch_api_page(
                session,
                offset,
            )

            if data is None:

                raise RuntimeError(
                    "Could not retrieve " "the current opportunity list."
                )

            hits = data.get(
                "hits",
                {},
            )

            total_info = hits.get(
                "total",
                {},
            )

            if total is None:

                if isinstance(
                    total_info,
                    dict,
                ):
                    total = total_info.get(
                        "value",
                        0,
                    )
                else:
                    total = int(total_info or 0)

                print(
                    f"API reports " f"{total} opportunities.",
                    flush=True,
                )

            page_hits = hits.get(
                "hits",
                [],
            )

            if not page_hits:
                break

            for hit in page_hits:

                source = hit.get(
                    "_source",
                    {},
                )

                opid = source.get("opid")

                if opid is None:
                    opid = hit.get("_id")

                if opid is None:
                    continue

                source["opid"] = int(opid)

                opportunities.append(source)

            offset += len(page_hits)

            print(
                f"Retrieved " f"{len(opportunities)}/" f"{total}",
                flush=True,
            )

            if total is not None and offset >= total:
                break

            if len(page_hits) < API_PAGE_SIZE:
                break

    finally:

        session.close()

    if total is not None and len(opportunities) != total:

        raise RuntimeError("Incomplete API retrieval: " f"{len(opportunities)}/{total}")

    return opportunities


# ============================================================
# DETAIL PAGE HELPERS
# ============================================================


def find_detail_card(
    soup: BeautifulSoup,
):

    for card in soup.find_all(
        "div",
        class_="card-content",
    ):

        headings = [
            heading.get_text(
                " ",
                strip=True,
            ).lower()
            for heading in card.find_all("h6")
        ]

        if "activity dates" in headings:
            return card

    return None


def get_section(
    card,
    heading_name: str,
) -> str | None:

    if card is None:
        return None

    for heading in card.find_all("h6"):

        current = heading.get_text(
            " ",
            strip=True,
        )

        if current.lower() != heading_name.lower():
            continue

        for sibling in heading.next_siblings:

            if (
                getattr(
                    sibling,
                    "name",
                    None,
                )
                == "p"
            ):

                return sibling.get_text(
                    " ",
                    strip=True,
                )

            if (
                getattr(
                    sibling,
                    "name",
                    None,
                )
                == "h6"
            ):

                break

    return None


def get_topics(
    card,
) -> list[str]:

    if card is None:
        return []

    for heading in card.find_all("h6"):

        if (
            heading.get_text(
                " ",
                strip=True,
            ).lower()
            != "activity topics"
        ):
            continue

        topics = []

        for sibling in heading.next_siblings:

            if (
                getattr(
                    sibling,
                    "name",
                    None,
                )
                == "h6"
            ):

                break

            if (
                getattr(
                    sibling,
                    "name",
                    None,
                )
                == "p"
            ):

                text = sibling.get_text(
                    " ",
                    strip=True,
                )

                if text:
                    topics.append(text)

        return topics

    return []


def get_image_url(
    soup: BeautifulSoup,
) -> str | None:
    """Extract the opportunity image URL from the detail page."""

    if soup is None:
        return None

    # Try to find image in various common locations
    # 1. Try img tag in header area
    for img in soup.find_all("img"):
        src = img.get("src", "")
        alt = img.get("alt", "").lower()

        if src and "opportunity" in alt or "opportunity" in src:
            return src

    # 2. Try background-image style in header
    for div in soup.find_all("div"):
        style = div.get("style", "")

        if "background-image" in style:
            match = re.search(
                r"url\(['\"]?([^'\"()]+)['\"]?\)",
                style,
            )

            if match:
                image_url = match.group(1)

                if image_url and "opportunity" in image_url:
                    return image_url

    # 3. Try common opportunity image classes
    for div in soup.find_all(
        "div",
        class_=re.compile(r"opportunity|hero|banner|image"),
    ):
        for img in div.find_all("img"):
            src = img.get("src")

            if src:
                return src

        style = div.get("style", "")

        if "background-image" in style:
            match = re.search(
                r"url\(['\"]?([^'\"()]+)['\"]?\)",
                style,
            )

            if match:
                return match.group(1)

    return None


def parse_dates(
    text: str | None,
) -> list[datetime]:

    if not text:
        return []

    values = re.findall(
        r"\d{2}/\d{2}/\d{4}",
        text,
    )

    dates = []

    for value in values:

        try:

            dates.append(
                datetime.strptime(
                    value,
                    "%d/%m/%Y",
                )
            )

        except ValueError:
            pass

    return dates


# ============================================================
# DETAIL REQUEST
# ============================================================


def fetch_detail_page(
    session: requests.Session,
    opportunity: dict,
) -> tuple[str, str | None]:

    opid = int(opportunity["opid"])

    url = f"{BASE_URL}/solidarity/" f"opportunity/{opid}_en"

    print(
        f"  → Requesting {opid}",
        flush=True,
    )

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        try:

            response = session.get(
                url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code == 200:

                print(
                    f"  ← {opid}: HTTP 200",
                    flush=True,
                )

                return (
                    "200",
                    response.text,
                )

            if response.status_code == 404:

                print(
                    f"  ← {opid}: HTTP 404",
                    flush=True,
                )

                return (
                    "404",
                    None,
                )

            if response.status_code == 429:

                wait = get_retry_after_seconds(response)

                print(
                    f"  ← {opid}: HTTP 429",
                    flush=True,
                )

                if attempt >= MAX_RETRIES:

                    print(
                        "  Rate limit persisted. " "Stopping this batch.",
                        flush=True,
                    )

                    return (
                        "429",
                        None,
                    )

                print(
                    f"  Waiting {wait}s "
                    f"before retry "
                    f"{attempt}/{MAX_RETRIES}...",
                    flush=True,
                )

                time.sleep(wait)

                continue

            if response.status_code >= 500:

                print(
                    f"  ← {opid}: " f"HTTP {response.status_code}",
                    flush=True,
                )

                if attempt < MAX_RETRIES:

                    wait = 2**attempt

                    print(
                        f"  Retrying in " f"{wait}s...",
                        flush=True,
                    )

                    time.sleep(wait)

                    continue

                return (
                    f"HTTP_{response.status_code}",
                    None,
                )

            print(
                f"  ← {opid}: " f"HTTP {response.status_code}",
                flush=True,
            )

            return (
                f"HTTP_{response.status_code}",
                None,
            )

        except requests.Timeout:

            print(
                f"  ← {opid}: TIMEOUT",
                flush=True,
            )

            if attempt < MAX_RETRIES:

                wait = 2**attempt

                print(
                    f"  Retrying in " f"{wait}s...",
                    flush=True,
                )

                time.sleep(wait)

                continue

            return (
                "TIMEOUT",
                None,
            )

        except requests.RequestException as exc:

            print(
                f"  ← {opid}: " f"REQUEST ERROR: {exc}",
                flush=True,
            )

            if attempt < MAX_RETRIES:

                wait = 2**attempt

                print(
                    f"  Retrying in " f"{wait}s...",
                    flush=True,
                )

                time.sleep(wait)

                continue

            return (
                "ERROR",
                None,
            )

    return (
        "FAILED",
        None,
    )


# ============================================================
# DETAIL PARSER
# ============================================================


def parse_detail_page(
    opportunity: dict,
    html: str,
) -> dict:

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    card = find_detail_card(soup)

    if card is None:

        return {
            "status": "parse_error",
            "result": None,
        }

    participant_text = get_section(
        card,
        "Looking for participants from",
    )

    if not participant_text:

        return {
            "status": "not_morocco",
            "result": None,
        }

    countries = [country.strip() for country in participant_text.split(",")]

    morocco_eligible = any(
        country.lower() == TARGET_COUNTRY.lower() for country in countries
    )

    if not morocco_eligible:

        return {
            "status": "not_morocco",
            "result": None,
        }

    activity_text = get_section(
        card,
        "Activity dates",
    )

    location = get_section(
        card,
        "Activity location",
    )

    activity_type = get_section(
        card,
        "Activity type",
    )

    deadline_text = get_section(
        card,
        "Deadline for applications",
    )

    project_code = get_section(
        card,
        "Project code",
    )

    activity_dates = parse_dates(activity_text)

    start_date = activity_dates[0] if len(activity_dates) >= 1 else None

    end_date = activity_dates[1] if len(activity_dates) >= 2 else None

    deadline_dates = parse_dates(deadline_text)

    deadline = deadline_dates[0] if deadline_dates else None

    # --------------------------------------------------------
    # Defensive expiration checks
    # --------------------------------------------------------

    if deadline is not None and deadline < TODAY:

        return {
            "status": "expired_deadline",
            "result": None,
        }

    if end_date is not None and end_date < TODAY:

        return {
            "status": "activity_finished",
            "result": None,
        }

    result = {
        "id": int(opportunity["opid"]),
        "title": opportunity.get(
            "title",
            "",
        ),
        "location": (
            location
            or (
                f"{opportunity.get('town', '')}, " f"{opportunity.get('country', '')}"
            ).strip(", ")
        ),
        "country": opportunity.get(
            "country",
            "",
        ),
        "town": opportunity.get(
            "town",
            "",
        ),
        "activity_type": (activity_type or ""),
        "start_date": (start_date.strftime("%Y-%m-%d") if start_date else None),
        "end_date": (end_date.strftime("%Y-%m-%d") if end_date else None),
        "deadline": (deadline.strftime("%Y-%m-%d") if deadline else None),
        "eligible_countries": countries,
        "topics": get_topics(card),
        "project_code": (project_code or ""),
        "created": opportunity.get(
            "created",
            "",
        ),
        "image_url": get_image_url(soup),
        "url": (f"{BASE_URL}/solidarity/" f"opportunity/" f"{opportunity['opid']}_en"),
    }

    return {
        "status": "match",
        "result": result,
    }


# ============================================================
# ARCHIVE HELPERS
# ============================================================


def archive_match(
    history: dict,
    opid: str,
    result: dict,
    reason: str,
) -> None:

    history[opid] = {
        "first_seen": (
            history.get(opid, {}).get("first_seen") or result.get("created")
        ),
        "last_seen": now_iso(),
        "result": result,
        "reason": reason,
    }


def archive_disappeared_matches(
    processed: dict,
    history: dict,
    current_ids: set[str],
) -> int:

    archived_count = 0

    for opid, entry in processed.items():

        if entry.get("status") != "match":
            continue

        result = entry.get("result")

        if not result:
            continue

        if opid not in current_ids:

            archive_match(
                history,
                opid,
                result,
                ("No longer present in " "the active opportunity list."),
            )

            archived_count += 1

    return archived_count


def archive_previous_match(
    history: dict,
    opid: str,
    previous_entry: dict | None,
    reason: str,
) -> bool:

    if not previous_entry:
        return False

    if previous_entry.get("status") != "match":
        return False

    result = previous_entry.get("result")

    if not result:
        return False

    archive_match(
        history,
        opid,
        result,
        reason,
    )

    return True


# ============================================================
# PUBLIC OUTPUT
# ============================================================


def get_current_matches(
    checkpoint: dict,
    current_ids: set[str],
) -> list[dict]:

    processed = checkpoint.get(
        "processed",
        {},
    )

    matches = []

    for opid in current_ids:

        entry = processed.get(opid)

        if not entry:
            continue

        if entry.get("status") != "match":
            continue

        result = entry.get("result")

        if result:

            matches.append(result)

    matches.sort(
        key=lambda item: (
            item.get("deadline") or "9999-12-31",
            item.get(
                "title",
                "",
            ),
        )
    )

    return matches


def save_public_output(
    matches: list[dict],
) -> None:

    output = {
        "generated_at": now_iso(),
        "source_date": TODAY.strftime("%Y-%m-%d"),
        "country": TARGET_COUNTRY,
        "count": len(matches),
        "opportunities": matches,
    }

    atomic_write_json(
        OPPORTUNITIES_FILE,
        output,
    )


def save_expired_output(
    history: dict,
) -> None:

    archived = []

    for entry in history.values():

        result = entry.get("result")

        if not result:
            continue

        archived.append(
            {
                **result,
                "last_seen": entry.get("last_seen"),
                "reason": entry.get("reason"),
            }
        )

    archived.sort(
        key=lambda item: (
            item.get(
                "last_seen",
                "",
            )
        ),
        reverse=True,
    )

    archived = archived[:MAX_ARCHIVED_OPPORTUNITIES]

    output = {
        "generated_at": now_iso(),
        "count": len(archived),
        "opportunities": archived,
    }

    atomic_write_json(
        EXPIRED_FILE,
        output,
    )


# ============================================================
# WORK QUEUE
# ============================================================


def build_work_queue(
    current_opportunities: list[dict],
    checkpoint: dict,
) -> list[str]:
    """
    Queue rules:

    1. New opportunities:
       Never seen before → scan.

    2. Technical failures:
       Retry.

    3. Existing Morocco matches:
       Recheck every run.

    4. Previously scanned non-Morocco opportunities:
       Skip.

    5. Archived opportunities that disappeared:
       Skip.

    This is what allows the initial ~1200 opportunity scan
    to eventually turn into a very small daily workload.
    """

    processed = checkpoint.get(
        "processed",
        {},
    )

    ordered_ids = [str(opportunity["opid"]) for opportunity in current_opportunities]

    new_ids = []
    retry_ids = []
    match_ids = []

    for opid in ordered_ids:

        entry = processed.get(opid)

        # ----------------------------------------------------
        # New opportunity.
        # ----------------------------------------------------

        if entry is None:

            new_ids.append(opid)

            continue

        status = entry.get("status")

        # ----------------------------------------------------
        # Retry technical problems.
        # ----------------------------------------------------

        if status in {
            "error",
            "parse_error",
            "timeout",
        }:

            retry_ids.append(opid)

            continue

        # ----------------------------------------------------
        # EXISTING MOROCCO MATCH.
        #
        # Recheck every run.
        # ----------------------------------------------------

        if status == "match":

            match_ids.append(opid)

            continue

        # ----------------------------------------------------
        # not_morocco
        # not_found
        # expired_deadline
        # activity_finished
        #
        # Intentionally skipped.
        # ----------------------------------------------------

    return new_ids + retry_ids + match_ids


# ============================================================
# MAIN
# ============================================================


def main() -> int:

    print("=" * 70)
    print("EU SOLIDARITY CORPS — " "MOROCCO OPPORTUNITY FINDER")
    print("=" * 70)

    print(
        f"Date: " f"{TODAY.strftime('%d/%m/%Y')}",
        flush=True,
    )

    print(
        f"Batch size: {BATCH_SIZE}",
        flush=True,
    )

    print(
        f"Detail request delay: " f"{DETAIL_REQUEST_DELAY}s",
        flush=True,
    )

    # --------------------------------------------------------
    # 1. Fetch a fresh API snapshot.
    # --------------------------------------------------------

    current_opportunities = fetch_current_opportunities()

    if not current_opportunities:

        raise RuntimeError("No current opportunities retrieved.")

    current_ids = {str(opportunity["opid"]) for opportunity in current_opportunities}

    opportunities_by_id = {
        str(opportunity["opid"]): opportunity for opportunity in current_opportunities
    }

    # --------------------------------------------------------
    # 2. Load persistent state.
    # --------------------------------------------------------

    checkpoint = load_checkpoint()

    processed = checkpoint["processed"]

    history = checkpoint["history"]

    # --------------------------------------------------------
    # 3. Archive Morocco matches that disappeared from the
    #    active API.
    # --------------------------------------------------------

    disappeared_count = archive_disappeared_matches(
        processed,
        history,
        current_ids,
    )

    if disappeared_count:

        print(
            f"Archived "
            f"{disappeared_count} "
            f"opportunity/opportunities "
            f"that disappeared from "
            f"the active list.",
            flush=True,
        )

        save_checkpoint(checkpoint)

    # --------------------------------------------------------
    # 4. Build current work queue.
    # --------------------------------------------------------

    queue = build_work_queue(
        current_opportunities,
        checkpoint,
    )

    already_processed = sum(1 for opid in current_ids if opid in processed)

    new_count = sum(1 for opid in current_ids if opid not in processed)

    existing_match_count = sum(
        1 for opid in current_ids if (processed.get(opid, {}).get("status") == "match")
    )

    batch = queue[:BATCH_SIZE]

    # --------------------------------------------------------
    # 5. Print plan.
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("SCAN PLAN")
    print("=" * 70)

    print(f"Current opportunities: " f"{len(current_opportunities)}")

    print(f"Already processed: " f"{already_processed}")

    print(f"New opportunities: " f"{new_count}")

    print(f"Existing Morocco matches: " f"{existing_match_count}")

    print(f"Work remaining: " f"{len(queue)}")

    print(f"This batch: " f"{len(batch)}")

    print("=" * 70)

    # --------------------------------------------------------
    # 6. Nothing to scan.
    # --------------------------------------------------------

    if not batch:

        current_matches = get_current_matches(
            checkpoint,
            current_ids,
        )

        save_public_output(current_matches)

        save_expired_output(history)

        save_checkpoint(checkpoint)

        print(
            "\n" "NO DETAIL SCANNING REQUIRED",
            flush=True,
        )

        print(
            f"Current Morocco matches: " f"{len(current_matches)}",
            flush=True,
        )

        print(
            "All current non-Morocco "
            "opportunities are already "
            "known and are being skipped.",
            flush=True,
        )

        return 0

    # --------------------------------------------------------
    # 7. Cooldown before detail scanning.
    # --------------------------------------------------------

    print(
        f"\nWaiting " f"{DETAIL_SCAN_COOLDOWN}s " f"before detail scanning...",
        flush=True,
    )

    time.sleep(DETAIL_SCAN_COOLDOWN)

    # --------------------------------------------------------
    # 8. Process this batch.
    # --------------------------------------------------------

    session = requests.Session()

    processed_this_batch = 0
    new_matches = 0
    archived_this_batch = 0

    rate_limited = False

    try:

        for index, opid in enumerate(
            batch,
            start=1,
        ):

            opportunity = opportunities_by_id[opid]

            previous_entry = processed.get(opid)

            print(
                "\n" + "=" * 60,
                flush=True,
            )

            print(
                f"[{index}/{len(batch)}] " f"Checking ID {opid}",
                flush=True,
            )

            status, html = fetch_detail_page(
                session,
                opportunity,
            )

            # ------------------------------------------------
            # RATE LIMIT
            # ------------------------------------------------

            if status == "429":

                rate_limited = True

                print(
                    "\n" + "!" * 60,
                    flush=True,
                )

                print(
                    "RATE LIMIT DETECTED",
                    flush=True,
                )

                print(
                    "Stopping this batch safely.",
                    flush=True,
                )

                break

            processed_this_batch += 1

            checked_at = now_iso()

            # ------------------------------------------------
            # 404
            # ------------------------------------------------

            if status == "404":

                processed[opid] = {
                    "status": "not_found",
                    "result": None,
                    "checked_at": checked_at,
                }

            # ------------------------------------------------
            # Technical error
            # ------------------------------------------------

            elif status != "200":

                processed[opid] = {
                    "status": "error",
                    "http_status": status,
                    "result": None,
                    "checked_at": checked_at,
                }

            # ------------------------------------------------
            # Successful page
            # ------------------------------------------------

            else:

                parsed = parse_detail_page(
                    opportunity,
                    html,
                )

                new_status = parsed.get("status")

                # --------------------------------------------
                # A previous Morocco match stopped qualifying.
                # Archive the previous result before replacing
                # the checkpoint entry.
                # --------------------------------------------

                if (
                    previous_entry
                    and previous_entry.get("status") == "match"
                    and new_status != "match"
                ):

                    if new_status == "not_morocco":

                        if archive_previous_match(
                            history,
                            opid,
                            previous_entry,
                            (
                                "No longer lists "
                                "Morocco among the "
                                "eligible participant "
                                "countries."
                            ),
                        ):

                            archived_this_batch += 1

                    elif new_status == "expired_deadline":

                        if archive_previous_match(
                            history,
                            opid,
                            previous_entry,
                            ("Application deadline " "has expired."),
                        ):

                            archived_this_batch += 1

                    elif new_status == "activity_finished":

                        if archive_previous_match(
                            history,
                            opid,
                            previous_entry,
                            ("Activity has finished."),
                        ):

                            archived_this_batch += 1

                # --------------------------------------------
                # A previously archived opportunity has become
                # active again and is now a Morocco match.
                # Remove its archive entry.
                # --------------------------------------------

                if new_status == "match":

                    if opid in history:

                        del history[opid]

                    new_matches += 1

                    result = parsed["result"]

                    print(
                        "\n✅ MOROCCO MATCH",
                        flush=True,
                    )

                    print(
                        f"{result['id']} — " f"{result['title']}",
                        flush=True,
                    )

                    print(
                        f"Activity: "
                        f"{result['start_date']} "
                        f"→ "
                        f"{result['end_date']}",
                        flush=True,
                    )

                    print(
                        f"Deadline: " f"{result['deadline'] or 'No deadline'}",
                        flush=True,
                    )

                processed[opid] = {
                    **parsed,
                    "checked_at": checked_at,
                }

            # ------------------------------------------------
            # SAVE CHECKPOINT AFTER EVERY SUCCESSFULLY
            # HANDLED DETAIL PAGE.
            # ------------------------------------------------

            checkpoint["processed"] = processed

            checkpoint["history"] = history

            save_checkpoint(checkpoint)

            print(
                f"Checkpoint saved " f"after ID {opid}.",
                flush=True,
            )

            # ------------------------------------------------
            # Rate-limit-friendly delay.
            # ------------------------------------------------

            if index < len(batch):

                time.sleep(DETAIL_REQUEST_DELAY)

    finally:

        session.close()

    # --------------------------------------------------------
    # 9. Build the current public dataset.
    # --------------------------------------------------------

    current_matches = get_current_matches(
        checkpoint,
        current_ids,
    )

    save_public_output(current_matches)

    save_expired_output(history)

    save_checkpoint(checkpoint)

    # --------------------------------------------------------
    # 10. See what remains.
    # --------------------------------------------------------

    remaining_queue = build_work_queue(
        current_opportunities,
        checkpoint,
    )

    # --------------------------------------------------------
    # 11. Summary.
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("BATCH COMPLETE")
    print("=" * 70)

    print(f"Processed this batch: " f"{processed_this_batch}")

    print(f"Morocco matches found/rechecked: " f"{new_matches}")

    print(f"Archived this batch: " f"{archived_this_batch}")

    print(f"Current Morocco matches: " f"{len(current_matches)}")

    print(f"Remaining work: " f"{len(remaining_queue)}")

    print("=" * 70)

    # --------------------------------------------------------
    # 12. Rate-limit result.
    # --------------------------------------------------------

    if rate_limited:

        print(
            "⚠️ Rate limited. " "Checkpoint saved.",
            flush=True,
        )

        print(
            "The next run will resume " "from the checkpoint.",
            flush=True,
        )

        return 2

    # --------------------------------------------------------
    # 13. Normal batch result.
    # --------------------------------------------------------

    if remaining_queue:

        print(
            "More opportunities remain " "to be processed.",
            flush=True,
        )

        print(
            "The next workflow run " "will continue.",
            flush=True,
        )

    else:

        print(
            "🎉 Initial population scan " "is complete.",
            flush=True,
        )

        print(
            "Future runs should only "
            "process new opportunities "
            "and current Morocco matches.",
            flush=True,
        )

    return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        sys.exit(main())

    except KeyboardInterrupt:

        print(
            "\nInterrupted by user.",
            flush=True,
        )

        print(
            "Existing checkpoint progress " "has been preserved.",
            flush=True,
        )

        sys.exit(2)

    except Exception as exc:

        print(
            f"\nFATAL ERROR: {exc}",
            file=sys.stderr,
            flush=True,
        )

        sys.exit(1)
