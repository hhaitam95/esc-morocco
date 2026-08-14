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

API_PAGE_SIZE = 100

# Maximum number of detail pages handled by ONE invocation.
BATCH_SIZE = 150

# Delay between successful detail requests.
DETAIL_REQUEST_DELAY = 2.0

# Hard timeout for every individual HTTP request.
REQUEST_TIMEOUT = 20

# Retries for temporary network/server errors.
MAX_RETRIES = 2


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
# DATE
# ============================================================

TODAY = datetime.now().replace(
    hour=0,
    minute=0,
    second=0,
    microsecond=0,
)

TODAY_API = TODAY.strftime(
    "%Y-%m-%dT00:00:00"
)


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

        # Deadline is still valid.
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
# API RETRIEVAL
# ============================================================

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
                f"API request: "
                f"from={offset}, "
                f"size={API_PAGE_SIZE}",
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

                print(
                    "API rate limit: HTTP 429",
                    flush=True,
                )

                return None

            if response.status_code >= 500:

                if attempt < MAX_RETRIES:

                    wait = 2 ** attempt

                    print(
                        f"API HTTP "
                        f"{response.status_code}; "
                        f"retrying in {wait}s",
                        flush=True,
                    )

                    time.sleep(wait)
                    continue

                return None

            print(
                f"API error: "
                f"HTTP {response.status_code}",
                flush=True,
            )

            return None

        except requests.Timeout:

            if attempt < MAX_RETRIES:

                wait = 2 ** attempt

                print(
                    f"API timeout; "
                    f"retrying in {wait}s",
                    flush=True,
                )

                time.sleep(wait)
                continue

            print(
                "API timeout: giving up.",
                flush=True,
            )

            return None

        except requests.RequestException as exc:

            if attempt < MAX_RETRIES:

                wait = 2 ** attempt

                print(
                    f"API request error: {exc}; "
                    f"retrying in {wait}s",
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
                    "Could not retrieve the "
                    "current opportunity list."
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
                    total = int(
                        total_info or 0
                    )

                print(
                    f"API reports "
                    f"{total} opportunities.",
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

                opid = source.get(
                    "opid"
                )

                if opid is None:
                    opid = hit.get("_id")

                if opid is None:
                    continue

                source["opid"] = int(opid)

                opportunities.append(
                    source
                )

            offset += len(
                page_hits
            )

            print(
                f"Retrieved "
                f"{len(opportunities)}/{total}",
                flush=True,
            )

            if (
                total is not None
                and offset >= total
            ):
                break

            if len(page_hits) < API_PAGE_SIZE:
                break

    finally:

        session.close()

    if (
        total is not None
        and len(opportunities) != total
    ):

        raise RuntimeError(
            f"Incomplete API retrieval: "
            f"{len(opportunities)}/{total}"
        )

    return opportunities


# ============================================================
# CHECKPOINT
# ============================================================

def load_checkpoint() -> dict:

    if not CHECKPOINT_FILE.exists():

        return {
            "processed": {},
            "history": {},
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
            raise ValueError(
                "Invalid checkpoint."
            )

        data.setdefault(
            "processed",
            {},
        )

        data.setdefault(
            "history",
            {},
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
        }


def save_checkpoint(
    checkpoint: dict,
) -> None:

    checkpoint["updated_at"] = (
        datetime.now().isoformat()
    )

    temporary = CHECKPOINT_FILE.with_suffix(
        ".tmp"
    )

    with temporary.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            checkpoint,
            file,
            ensure_ascii=False,
            indent=2,
        )

    temporary.replace(
        CHECKPOINT_FILE
    )


# ============================================================
# DETAIL PAGE HELPERS
# ============================================================

def find_detail_card(soup):

    for card in soup.find_all(
        "div",
        class_="card-content",
    ):

        headings = [
            heading.get_text(
                " ",
                strip=True,
            ).lower()
            for heading
            in card.find_all("h6")
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

        if (
            current.lower()
            != heading_name.lower()
        ):
            continue

        for sibling in heading.next_siblings:

            if getattr(
                sibling,
                "name",
                None,
            ) == "p":

                return sibling.get_text(
                    " ",
                    strip=True,
                )

            if getattr(
                sibling,
                "name",
                None,
            ) == "h6":

                break

    return None


def get_topics(card) -> list[str]:

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

            if getattr(
                sibling,
                "name",
                None,
            ) == "h6":
                break

            if getattr(
                sibling,
                "name",
                None,
            ) == "p":

                text = sibling.get_text(
                    " ",
                    strip=True,
                )

                if text:
                    topics.append(text)

        return topics

    return []


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
# DETAIL PAGE FETCH
# ============================================================

def fetch_detail_page(
    session: requests.Session,
    opportunity: dict,
) -> tuple[str, str | None]:

    opid = int(
        opportunity["opid"]
    )

    url = (
        f"{BASE_URL}/solidarity/"
        f"opportunity/{opid}_en"
    )

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

                print(
                    f"  ← {opid}: HTTP 429",
                    flush=True,
                )

                return (
                    "429",
                    None,
                )

            if response.status_code >= 500:

                print(
                    f"  ← {opid}: "
                    f"HTTP {response.status_code}",
                    flush=True,
                )

                if attempt < MAX_RETRIES:

                    wait = 2 ** attempt

                    print(
                        f"  retrying in {wait}s",
                        flush=True,
                    )

                    time.sleep(wait)
                    continue

                return (
                    f"HTTP_{response.status_code}",
                    None,
                )

            print(
                f"  ← {opid}: "
                f"HTTP {response.status_code}",
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

                wait = 2 ** attempt

                print(
                    f"  retry "
                    f"{attempt}/{MAX_RETRIES - 1} "
                    f"in {wait}s",
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
                f"  ← {opid}: "
                f"REQUEST ERROR: {exc}",
                flush=True,
            )

            if attempt < MAX_RETRIES:

                wait = 2 ** attempt

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
# DETAIL PAGE PARSER
# ============================================================

def parse_detail_page(
    opportunity: dict,
    html: str,
) -> dict:

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    card = find_detail_card(
        soup
    )

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

    countries = [
        country.strip()
        for country
        in participant_text.split(",")
    ]

    if not any(
        country.lower()
        == TARGET_COUNTRY.lower()
        for country in countries
    ):

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

    activity_dates = parse_dates(
        activity_text
    )

    start_date = (
        activity_dates[0]
        if len(activity_dates) >= 1
        else None
    )

    end_date = (
        activity_dates[1]
        if len(activity_dates) >= 2
        else None
    )

    deadline_dates = parse_dates(
        deadline_text
    )

    deadline = (
        deadline_dates[0]
        if deadline_dates
        else None
    )

    # --------------------------------------------------------
    # Defensive filters
    # --------------------------------------------------------

    if (
        deadline is not None
        and deadline < TODAY
    ):

        return {
            "status": "expired_deadline",
            "result": None,
        }

    if (
        end_date is not None
        and end_date < TODAY
    ):

        return {
            "status": "activity_finished",
            "result": None,
        }

    result = {
        "id": int(
            opportunity["opid"]
        ),
        "title": opportunity.get(
            "title",
            "",
        ),
        "location": (
            location
            or (
                f"{opportunity.get('town', '')}, "
                f"{opportunity.get('country', '')}"
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
        "activity_type": (
            activity_type
            or ""
        ),
        "start_date": (
            start_date.strftime(
                "%Y-%m-%d"
            )
            if start_date
            else None
        ),
        "end_date": (
            end_date.strftime(
                "%Y-%m-%d"
            )
            if end_date
            else None
        ),
        "deadline": (
            deadline.strftime(
                "%Y-%m-%d"
            )
            if deadline
            else None
        ),
        "eligible_countries": countries,
        "topics": get_topics(
            card
        ),
        "project_code": (
            project_code
            or ""
        ),
        "created": opportunity.get(
            "created",
            "",
        ),
        "url": (
            f"{BASE_URL}/solidarity/"
            f"opportunity/"
            f"{opportunity['opid']}_en"
        ),
    }

    return {
        "status": "match",
        "result": result,
    }


# ============================================================
# PUBLIC OUTPUT
# ============================================================

def get_current_matches(
    checkpoint: dict,
    current_ids: set[str],
) -> list[dict]:

    matches = []

    processed = checkpoint.get(
        "processed",
        {},
    )

    for opid in current_ids:

        entry = processed.get(
            opid
        )

        if not entry:
            continue

        if (
            entry.get("status")
            != "match"
        ):
            continue

        result = entry.get(
            "result"
        )

        if result:
            matches.append(
                result
            )

    matches.sort(
        key=lambda item: (
            item.get("deadline")
            or "9999-12-31",
            item.get("title", ""),
        )
    )

    return matches


def save_public_output(
    matches: list[dict],
) -> None:

    output = {
        "generated_at": datetime.now().isoformat(),
        "source_date": TODAY.strftime(
            "%Y-%m-%d"
        ),
        "country": TARGET_COUNTRY,
        "count": len(matches),
        "opportunities": matches,
    }

    temporary = OPPORTUNITIES_FILE.with_suffix(
        ".tmp"
    )

    with temporary.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2,
        )

    temporary.replace(
        OPPORTUNITIES_FILE
    )


def save_expired_output(
    expired: list[dict],
) -> None:

    expired.sort(
        key=lambda item: (
            item.get(
                "last_seen",
                "",
            )
        ),
        reverse=True,
    )

    # Keep the last 30.
    expired = expired[:30]

    output = {
        "generated_at": datetime.now().isoformat(),
        "count": len(expired),
        "opportunities": expired,
    }

    temporary = EXPIRED_FILE.with_suffix(
        ".tmp"
    )

    with temporary.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2,
        )

    temporary.replace(
        EXPIRED_FILE
    )


# ============================================================
# BUILD WORK QUEUE
# ============================================================

def build_work_queue(
    current_opportunities: list[dict],
    checkpoint: dict,
) -> list[str]:

    processed = checkpoint.get(
        "processed",
        {},
    )

    current_ids = {
        str(
            opportunity["opid"]
        )
        for opportunity
        in current_opportunities
    }

    # New opportunities first.
    new_ids = [
        opid
        for opid in current_ids
        if opid not in processed
    ]

    # Re-check existing Morocco matches.
    existing_match_ids = [
        opid
        for opid in current_ids
        if (
            opid in processed
            and processed[opid].get("status")
            == "match"
        )
    ]

    # Retry previous technical failures.
    retry_ids = [
        opid
        for opid in current_ids
        if (
            opid in processed
            and processed[opid].get("status")
            in {
                "error",
                "parse_error",
                "timeout",
            }
        )
    ]

    # Maintain deterministic order using API order.
    ordered_ids = [
        str(
            opportunity["opid"]
        )
        for opportunity
        in current_opportunities
    ]

    priority = (
        set(new_ids)
        | set(existing_match_ids)
        | set(retry_ids)
    )

    return [
        opid
        for opid in ordered_ids
        if opid in priority
    ]


# ============================================================
# MAIN
# ============================================================

def main() -> int:

    print("=" * 70)
    print(
        "EU SOLIDARITY CORPS — "
        "MOROCCO OPPORTUNITY FINDER"
    )
    print("=" * 70)

    print(
        f"Date: "
        f"{TODAY.strftime('%d/%m/%Y')}",
        flush=True,
    )

    print(
        f"Batch size: "
        f"{BATCH_SIZE}",
        flush=True,
    )

    # --------------------------------------------------------
    # Current API dataset
    # --------------------------------------------------------

    current_opportunities = (
        fetch_current_opportunities()
    )

    if not current_opportunities:

        raise RuntimeError(
            "No current opportunities retrieved."
        )

    current_ids = {
        str(
            opportunity["opid"]
        )
        for opportunity
        in current_opportunities
    }

    opportunities_by_id = {
        str(
            opportunity["opid"]
        ): opportunity
        for opportunity
        in current_opportunities
    }

    # --------------------------------------------------------
    # Checkpoint
    # --------------------------------------------------------

    checkpoint = load_checkpoint()

    processed = checkpoint[
        "processed"
    ]

    history = checkpoint[
        "history"
    ]

    # --------------------------------------------------------
    # Work queue
    # --------------------------------------------------------

    queue = build_work_queue(
        current_opportunities,
        checkpoint,
    )

    total_current = len(
        current_opportunities
    )

    already_processed = sum(
        1
        for opid in current_ids
        if opid in processed
    )

    batch = queue[
        :BATCH_SIZE
    ]

    print("\n")
    print("=" * 70)
    print("BATCH PLAN")
    print("=" * 70)

    print(
        f"Current opportunities: "
        f"{total_current}"
    )

    print(
        f"Already processed: "
        f"{already_processed}"
    )

    print(
        f"Work remaining: "
        f"{len(queue)}"
    )

    print(
        f"This batch: "
        f"{len(batch)}"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # Detect old matches that disappeared from active list.
    # --------------------------------------------------------

    for opid, entry in processed.items():

        if (
            entry.get("status")
            != "match"
        ):
            continue

        result = entry.get(
            "result"
        )

        if not result:
            continue

        if (
            opid not in current_ids
            and opid not in history
        ):

            history[opid] = {
                "first_seen": result.get(
                    "created"
                ),
                "last_seen": (
                    checkpoint.get(
                        "updated_at"
                    )
                ),
                "result": result,
                "reason": (
                    "No longer present in "
                    "the active opportunity list."
                ),
            }

    # --------------------------------------------------------
    # If there's nothing to process
    # --------------------------------------------------------

    if not batch:

        current_matches = (
            get_current_matches(
                checkpoint,
                current_ids,
            )
        )

        save_public_output(
            current_matches
        )

        expired = [
            {
                **entry["result"],
                "last_seen": entry.get(
                    "last_seen"
                ),
                "reason": entry.get(
                    "reason"
                ),
            }
            for entry
            in history.values()
            if entry.get("result")
        ]

        save_expired_output(
            expired
        )

        save_checkpoint(
            checkpoint
        )

        print("\n")
        print("=" * 70)
        print("NOTHING NEW TO PROCESS")
        print("=" * 70)

        print(
            f"Current Morocco matches: "
            f"{len(current_matches)}"
        )

        return 0

    # --------------------------------------------------------
    # Detail scan
    # --------------------------------------------------------

    session = requests.Session()

    processed_this_batch = 0
    matches_this_batch = 0
    rate_limited = False

    try:

        for index, opid in enumerate(
            batch,
            start=1,
        ):

            opportunity = (
                opportunities_by_id[opid]
            )

            print(
                "\n"
                + "=" * 60,
                flush=True,
            )

            print(
                f"[{index}/{len(batch)}] "
                f"Checking ID {opid}",
                flush=True,
            )

            status, html = (
                fetch_detail_page(
                    session,
                    opportunity,
                )
            )

            if status == "429":

                print(
                    "\nRATE LIMIT DETECTED.",
                    flush=True,
                )

                print(
                    "Stopping this batch safely.",
                    flush=True,
                )

                rate_limited = True
                break

            processed_this_batch += 1

            # ------------------------------------------------
            # Save result
            # ------------------------------------------------

            if status == "404":

                processed[opid] = {
                    "status": "not_found",
                    "result": None,
                    "checked_at": datetime.now().isoformat(),
                }

            elif status != "200":

                processed[opid] = {
                    "status": "error",
                    "http_status": status,
                    "result": None,
                    "checked_at": datetime.now().isoformat(),
                }

            else:

                parsed = parse_detail_page(
                    opportunity,
                    html,
                )

                processed[opid] = {
                    **parsed,
                    "checked_at": datetime.now().isoformat(),
                }

                if (
                    parsed["status"]
                    == "match"
                ):

                    matches_this_batch += 1

                    result = parsed[
                        "result"
                    ]

                    print(
                        "\n✅ MOROCCO MATCH",
                        flush=True,
                    )

                    print(
                        f"{result['id']} — "
                        f"{result['title']}",
                        flush=True,
                    )

                    print(
                        f"Activity: "
                        f"{result['start_date']} → "
                        f"{result['end_date']}",
                        flush=True,
                    )

                    print(
                        f"Deadline: "
                        f"{result['deadline'] or 'No deadline'}",
                        flush=True,
                    )

            # ------------------------------------------------
            # Save after EVERY opportunity.
            # ------------------------------------------------

            checkpoint["processed"] = (
                processed
            )

            checkpoint["history"] = (
                history
            )

            save_checkpoint(
                checkpoint
            )

            # Update public JSON too.
            current_matches = (
                get_current_matches(
                    checkpoint,
                    current_ids,
                )
            )

            save_public_output(
                current_matches
            )

            time.sleep(
                DETAIL_REQUEST_DELAY
            )

    finally:

        session.close()

    # --------------------------------------------------------
    # Finalize outputs
    # --------------------------------------------------------

    current_matches = (
        get_current_matches(
            checkpoint,
            current_ids,
        )
    )

    save_public_output(
        current_matches
    )

    expired = [
        {
            **entry["result"],
            "last_seen": entry.get(
                "last_seen"
            ),
            "reason": entry.get(
                "reason"
            ),
        }
        for entry
        in history.values()
        if entry.get("result")
    ]

    save_expired_output(
        expired
    )

    save_checkpoint(
        checkpoint
    )

    remaining = max(
        0,
        len(
            build_work_queue(
                current_opportunities,
                checkpoint,
            )
        )
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("BATCH COMPLETE")
    print("=" * 70)

    print(
        f"Processed this batch: "
        f"{processed_this_batch}"
    )

    print(
        f"Matches this batch: "
        f"{matches_this_batch}"
    )

    print(
        f"Current Morocco matches: "
        f"{len(current_matches)}"
    )

    print(
        f"Remaining work: "
        f"{remaining}"
    )

    print("=" * 70)

    if rate_limited:

        print(
            "⚠️ Rate limited. "
            "Checkpoint saved."
        )

        # Exit 2 means:
        # "Pause; rerun later."
        return 2

    if remaining > 0:

        print(
            "More batches remain."
        )

        # Exit 0 because the batch itself succeeded.
        # GitHub Actions can invoke another batch.
        return 0

    print(
        "🎉 Current opportunity population "
        "has been fully processed."
    )

    return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        sys.exit(
            main()
        )

    except KeyboardInterrupt:

        print(
            "\nInterrupted. "
            "Checkpoint already saved."
        )

        sys.exit(2)

    except Exception as exc:

        print(
            f"\nFATAL ERROR: {exc}",
            file=sys.stderr,
        )

        sys.exit(1)