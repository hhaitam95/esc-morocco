import json
import os
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

# Conservative rate for detail pages.
# The portal has previously returned 429 after sustained traffic.
DETAIL_REQUEST_DELAY = 2.0

REQUEST_TIMEOUT = 20
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
# HTTP
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
    Build the same search request used by the portal.
    """

    return {
        "type": "Opportunity",
        "size": API_PAGE_SIZE,
        "from": offset,

        # Only open opportunities.
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

        # Include opportunities without deadlines.
        "filters[has_no_deadline][value]": "true",
        "filters[has_no_deadline][type]": "must",
        "filters[has_no_deadline][group]": "deadline",

        # Fields required by the application.
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
# FETCH API
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
                    "\n[API 429] "
                    "The portal is rate-limiting us."
                )

                return None

            if response.status_code >= 500:

                if attempt < MAX_RETRIES:

                    wait = 2 ** attempt

                    print(
                        f"[API {response.status_code}] "
                        f"Retrying in {wait}s..."
                    )

                    time.sleep(wait)
                    continue

                return None

            print(
                f"[API ERROR] "
                f"HTTP {response.status_code}"
            )

            return None

        except requests.RequestException as exc:

            if attempt < MAX_RETRIES:

                wait = 2 ** attempt

                print(
                    f"[API ERROR] {exc}"
                )

                print(
                    f"Retrying in {wait}s..."
                )

                time.sleep(wait)
                continue

            print(
                f"[API FAILED] {exc}"
            )

            return None

    return None


def fetch_current_opportunities() -> list[dict]:
    """
    Always retrieve a fresh opportunity list.

    There is intentionally NO permanent API cache.
    """

    print("=" * 70)
    print("FETCHING CURRENT OPPORTUNITIES")
    print("=" * 70)

    session = requests.Session()

    opportunities = []

    offset = 0
    total = None

    try:

        while True:

            print(
                f"API: from={offset}, "
                f"size={API_PAGE_SIZE}"
            )

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
                    f"{total} opportunities."
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
                    opid = hit.get(
                        "_id"
                    )

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
                f"{len(opportunities)}"
                f"/{total}"
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

            data = json.load(
                file
            )

        if not isinstance(
            data,
            dict,
        ):
            raise ValueError(
                "Checkpoint is not an object."
            )

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

        return data

    except (
        OSError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:

        print(
            f"Could not read checkpoint: {exc}"
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
# DETAIL PAGE PARSING
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
                    topics.append(
                        text
                    )

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
# DETAIL PAGE REQUEST
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

                return (
                    "200",
                    response.text,
                )

            if response.status_code == 404:

                return (
                    "404",
                    None,
                )

            if response.status_code == 429:

                return (
                    "429",
                    None,
                )

            if response.status_code >= 500:

                if attempt < MAX_RETRIES:

                    wait = 2 ** attempt

                    print(
                        f"HTTP {response.status_code} "
                        f"for {opid}; "
                        f"retrying in {wait}s..."
                    )

                    time.sleep(
                        wait
                    )

                    continue

                return (
                    f"HTTP_{response.status_code}",
                    None,
                )

            return (
                f"HTTP_{response.status_code}",
                None,
            )

        except requests.Timeout:

            if attempt < MAX_RETRIES:

                wait = 2 ** attempt

                print(
                    f"Timeout for {opid}; "
                    f"retrying in {wait}s..."
                )

                time.sleep(
                    wait
                )

                continue

            return (
                "TIMEOUT",
                None,
            )

        except requests.RequestException as exc:

            if attempt < MAX_RETRIES:

                wait = 2 ** attempt

                print(
                    f"Request error for {opid}: "
                    f"{exc}"
                )

                time.sleep(
                    wait
                )

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
# PARSE DETAIL PAGE
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

    morocco_eligible = any(
        country.lower()
        == TARGET_COUNTRY.lower()
        for country in countries
    )

    if not morocco_eligible:

        return {
            "status": "not_morocco",
            "result": None,
        }

    # --------------------------------------------------------
    # Other fields
    # --------------------------------------------------------

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
    # Defensive filtering
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

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

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

    # Newest expiration first.
    expired.sort(
        key=lambda item: (
            item.get(
                "last_seen",
                "",
            ),
        ),
        reverse=True,
    )

    # Keep only the 30 most recent.
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
        f"{TODAY.strftime('%d/%m/%Y')}"
    )

    # --------------------------------------------------------
    # 1. Fresh API data
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
    # 2. Load checkpoint
    # --------------------------------------------------------

    checkpoint = load_checkpoint()

    processed = checkpoint[
        "processed"
    ]

    history = checkpoint[
        "history"
    ]

    # --------------------------------------------------------
    # 3. Identify what needs checking
    # --------------------------------------------------------

    new_ids = [
        opid
        for opid in current_ids
        if opid not in processed
    ]

    # Existing Morocco matches need periodic revalidation
    # because their deadlines/eligibility can change.
    existing_match_ids = [
        opid
        for opid in current_ids
        if (
            opid in processed
            and processed[opid].get(
                "status"
            ) == "match"
        )
    ]

    # Errors/parse errors should be retried.
    retry_ids = [
        opid
        for opid in current_ids
        if (
            opid in processed
            and processed[opid].get(
                "status"
            ) in {
                "error",
                "parse_error",
                "timeout",
            }
        )
    ]

    ids_to_check = list(
        dict.fromkeys(
            new_ids
            + existing_match_ids
            + retry_ids
        )
    )

    print("\n")
    print("=" * 70)
    print("SCAN PLAN")
    print("=" * 70)

    print(
        f"Current opportunities: "
        f"{len(current_opportunities)}"
    )

    print(
        f"New opportunities:     "
        f"{len(new_ids)}"
    )

    print(
        f"Existing matches:      "
        f"{len(existing_match_ids)}"
    )

    print(
        f"Retry errors:           "
        f"{len(retry_ids)}"
    )

    print(
        f"Pages to check:        "
        f"{len(ids_to_check)}"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # 4. Detect previously matched opportunities that
    #    disappeared from the active API list.
    #
    #    We don't claim they definitely expired; we label
    #    them as no longer active on the portal.
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
                "last_seen": checkpoint.get(
                    "updated_at"
                ),
                "result": result,
                "reason": (
                    "No longer present in "
                    "the active opportunity list."
                ),
            }

    # --------------------------------------------------------
    # 5. Detail scanning
    # --------------------------------------------------------

    session = requests.Session()

    processed_this_run = 0
    matches_found_this_run = 0

    rate_limited = False

    try:

        for opid in ids_to_check:

            opportunity = (
                opportunities_by_id[opid]
            )

            processed_this_run += 1

            print(
                f"\n[{processed_this_run}/"
                f"{len(ids_to_check)}] "
                f"Checking ID {opid}..."
            )

            status, html = (
                fetch_detail_page(
                    session,
                    opportunity,
                )
            )

            # ------------------------------------------------
            # RATE LIMIT
            # ------------------------------------------------

            if status == "429":

                print(
                    "\n"
                    + "=" * 70
                )

                print(
                    "RATE LIMIT DETECTED"
                )

                print(
                    f"Stopped before "
                    f"completing ID {opid}."
                )

                print(
                    "All completed progress "
                    "has been saved."
                )

                print("=" * 70)

                rate_limited = True

                break

            # ------------------------------------------------
            # Result handling
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

                    matches_found_this_run += 1

                    result = parsed[
                        "result"
                    ]

                    print(
                        "\n✅ MATCH"
                    )

                    print(
                        f"{result['id']} — "
                        f"{result['title']}"
                    )

                    print(
                        f"   "
                        f"{result['start_date']} "
                        f"→ "
                        f"{result['end_date']}"
                    )

                    print(
                        f"   Deadline: "
                        f"{result['deadline'] or 'None'}"
                    )

            # ------------------------------------------------
            # Save checkpoint after EVERY successful request
            # ------------------------------------------------

            checkpoint["processed"] = processed
            checkpoint["history"] = history

            save_checkpoint(
                checkpoint
            )

            # Small delay
            time.sleep(
                DETAIL_REQUEST_DELAY
            )

    finally:

        session.close()

    # --------------------------------------------------------
    # 6. Build current public matches
    # --------------------------------------------------------

    current_matches = get_current_matches(
        checkpoint,
        current_ids,
    )

    save_public_output(
        current_matches
    )

    # --------------------------------------------------------
    # 7. Build expired/no-longer-active list
    # --------------------------------------------------------

    expired = []

    for entry in history.values():

        result = entry.get(
            "result"
        )

        if not result:
            continue

        expired.append({
            **result,
            "last_seen": entry.get(
                "last_seen"
            ),
            "reason": entry.get(
                "reason"
            ),
        })

    save_expired_output(
        expired
    )

    # --------------------------------------------------------
    # 8. Summary
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("RUN COMPLETE")
    print("=" * 70)

    print(
        f"Current opportunities: "
        f"{len(current_opportunities)}"
    )

    print(
        f"New opportunities: "
        f"{len(new_ids)}"
    )

    print(
        f"Checked this run: "
        f"{processed_this_run}"
    )

    print(
        f"New matches this run: "
        f"{matches_found_this_run}"
    )

    print(
        f"Current Morocco matches: "
        f"{len(current_matches)}"
    )

    print(
        f"Recently inactive matches: "
        f"{len(expired)}"
    )

    print(
        f"\nGenerated:"
    )

    print(
        OPPORTUNITIES_FILE
    )

    print(
        EXPIRED_FILE
    )

    print(
        "\nCheckpoint:"
    )

    print(
        CHECKPOINT_FILE
    )

    if rate_limited:

        print(
            "\n⚠️ Rate limited."
        )

        print(
            "Run again later to continue."
        )

        # Exit code 2 means "rate limited / resumable"
        return 2

    print(
        "\n✅ Scan completed without rate limiting."
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
            "\nInterrupted by user."
        )

        print(
            "Progress already saved."
        )

        sys.exit(2)

    except Exception as exc:

        print(
            f"\nERROR: {exc}",
            file=sys.stderr,
        )

        sys.exit(1)