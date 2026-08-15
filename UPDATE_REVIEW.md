# ESC Opportunity Finder — Participant Country Filtering

## Feature

Country-neutral participant eligibility filtering.

## Architecture

- Scraper stores eligible_countries for active opportunities.
- Public dataset exposes participant_countries.
- Frontend selects a participant country.
- Apply filters the active table locally.
- Active result count follows the applied filter.
- Existing destination-country filtering remains independent.
- Selection is persisted in localStorage.

## Migration safety

- Existing checkpoint migration is preserved.
- Generated data is not staged by the updater.
- GitHub Actions publishes the new dataset only after migration_complete is true.

## Validation

- app.js rebuilt from clean origin/main.
- JavaScript syntax passed.
- No duplicate participant-country declarations.
- Translation scope validated.
- Python scraper syntax passed.
- Workflow contract validated.
- Feature whitespace normalized.
- git diff --check passed.
- Protected generated files are not staged.

## Staged diff

```diff
diff --git a/.github/workflows/update.yml b/.github/workflows/update.yml
index 0df017e..770803c 100644
--- a/.github/workflows/update.yml
+++ b/.github/workflows/update.yml
@@ -1,4 +1,4 @@
-name: Update ESC Morocco Opportunities
+name: Update ESC Opportunities
 
 on:
   # Run automatically every hour.
@@ -110,7 +110,27 @@ jobs:
             # ------------------------------------------------
 
             if [ -f data/opportunities.json ]; then
-              cp data/opportunities.json web/opportunities.json
+              python - <<'PY'
+import json
+
+with open(
+    "data/opportunities.json",
+    "r",
+    encoding="utf-8",
+) as file:
+    data = json.load(file)
+
+if data.get("migration_complete") is True:
+    raise SystemExit(0)
+
+raise SystemExit(1)
+PY
+              if [ $? -eq 0 ]; then
+                cp data/opportunities.json web/opportunities.json
+                echo "Published complete country-neutral dataset."
+              else
+                echo "Migration incomplete; keeping published dataset."
+              fi
             fi
 
             if [ -f data/expired.json ]; then
@@ -131,7 +151,7 @@ jobs:
               git add web/expired.json
 
               git commit \
-                -m "Update ESC Morocco opportunities"
+                -m "Update ESC opportunities"
 
               git push
 
diff --git a/scraper/scraper.py b/scraper/scraper.py
index c0331c3..27b3f2c 100644
--- a/scraper/scraper.py
+++ b/scraper/scraper.py
@@ -15,7 +15,11 @@ from bs4 import BeautifulSoup
 BASE_URL = "https://youth.europa.eu"
 API_URL = f"{BASE_URL}/api/rest/eyp/v1/search_en"
 
-TARGET_COUNTRY = "Morocco"
+CHECKPOINT_SCHEMA_VERSION = 2
+
+# Recheck active opportunities at most once per day. This keeps the hourly workflow lightweight while still detecting participant-eligibility changes.
+DETAIL_RECHECK_INTERVAL = 24 * 60 * 60
+
 
 # ------------------------------------------------------------
 # API
@@ -207,28 +211,28 @@ def parse_iso_datetime(
 
 
 def load_checkpoint() -> dict:
-
     if not CHECKPOINT_FILE.exists():
         return {
+            "schema_version": CHECKPOINT_SCHEMA_VERSION,
             "processed": {},
             "history": {},
             "last_scan_at": None,
         }
 
     try:
-
         with CHECKPOINT_FILE.open(
             "r",
             encoding="utf-8",
         ) as file:
-
             data = json.load(file)
 
         if not isinstance(
             data,
             dict,
         ):
-            raise ValueError("Checkpoint is not a JSON object.")
+            raise ValueError(
+                "Checkpoint is not a JSON object."
+            )
 
         if not isinstance(
             data.get("processed"),
@@ -247,26 +251,29 @@ def load_checkpoint() -> dict:
             None,
         )
 
-        return data
+        return normalize_checkpoint_for_country_neutral_mode(
+            data,
+        )
 
     except (
         OSError,
         json.JSONDecodeError,
         ValueError,
     ) as exc:
-
         print(
             f"Could not read checkpoint: {exc}",
             flush=True,
         )
 
         return {
+            "schema_version": CHECKPOINT_SCHEMA_VERSION,
             "processed": {},
             "history": {},
             "last_scan_at": None,
         }
 
 
+
 def save_checkpoint(
     checkpoint: dict,
 ) -> None:
@@ -938,16 +945,16 @@ def parse_detail_page(
     opportunity: dict,
     html: str,
 ) -> dict:
-
     soup = BeautifulSoup(
         html,
         "html.parser",
     )
 
-    card = find_detail_card(soup)
+    card = find_detail_card(
+        soup,
+    )
 
     if card is None:
-
         return {
             "status": "parse_error",
             "result": None,
@@ -958,25 +965,17 @@ def parse_detail_page(
         "Looking for participants from",
     )
 
-    if not participant_text:
-
-        return {
-            "status": "not_morocco",
-            "result": None,
-        }
-
-    countries = [country.strip() for country in participant_text.split(",")]
-
-    morocco_eligible = any(
-        country.lower() == TARGET_COUNTRY.lower() for country in countries
-    )
-
-    if not morocco_eligible:
+    if participant_text:
+        countries = [
+            country.strip()
+            for country in participant_text.split(",")
+            if country.strip()
+        ]
 
-        return {
-            "status": "not_morocco",
-            "result": None,
-        }
+        eligibility_known = True
+    else:
+        countries = []
+        eligibility_known = False
 
     activity_text = get_section(
         card,
@@ -1003,36 +1002,58 @@ def parse_detail_page(
         "Project code",
     )
 
-    activity_dates = parse_dates(activity_text)
+    activity_dates = parse_dates(
+        activity_text,
+    )
 
-    start_date = activity_dates[0] if len(activity_dates) >= 1 else None
+    start_date = (
+        activity_dates[0]
+        if len(activity_dates) >= 1
+        else None
+    )
 
-    end_date = activity_dates[1] if len(activity_dates) >= 2 else None
+    end_date = (
+        activity_dates[1]
+        if len(activity_dates) >= 2
+        else None
+    )
 
-    deadline_dates = parse_dates(deadline_text)
+    deadline_dates = parse_dates(
+        deadline_text,
+    )
 
-    deadline = deadline_dates[0] if deadline_dates else None
+    deadline = (
+        deadline_dates[0]
+        if deadline_dates
+        else None
+    )
 
     # --------------------------------------------------------
-    # Defensive expiration checks
+    # Defensive expiration checks.
     # --------------------------------------------------------
 
-    if deadline is not None and deadline < TODAY:
-
+    if (
+        deadline is not None
+        and deadline < TODAY
+    ):
         return {
             "status": "expired_deadline",
             "result": None,
         }
 
-    if end_date is not None and end_date < TODAY:
-
+    if (
+        end_date is not None
+        and end_date < TODAY
+    ):
         return {
             "status": "activity_finished",
             "result": None,
         }
 
     result = {
-        "id": int(opportunity["opid"]),
+        "id": int(
+            opportunity["opid"]
+        ),
         "title": opportunity.get(
             "title",
             "",
@@ -1040,7 +1061,8 @@ def parse_detail_page(
         "location": (
             location
             or (
-                f"{opportunity.get('town', '')}, " f"{opportunity.get('country', '')}"
+                f"{opportunity.get('town', '')}, "
+                f"{opportunity.get('country', '')}"
             ).strip(", ")
         ),
         "country": opportunity.get(
@@ -1051,27 +1073,59 @@ def parse_detail_page(
             "town",
             "",
         ),
-        "activity_type": (activity_type or ""),
-        "start_date": (start_date.strftime("%Y-%m-%d") if start_date else None),
-        "end_date": (end_date.strftime("%Y-%m-%d") if end_date else None),
-        "deadline": (deadline.strftime("%Y-%m-%d") if deadline else None),
+        "activity_type": (
+            activity_type
+            or ""
+        ),
+        "start_date": (
+            start_date.strftime(
+                "%Y-%m-%d",
+            )
+            if start_date
+            else None
+        ),
+        "end_date": (
+            end_date.strftime(
+                "%Y-%m-%d",
+            )
+            if end_date
+            else None
+        ),
+        "deadline": (
+            deadline.strftime(
+                "%Y-%m-%d",
+            )
+            if deadline
+            else None
+        ),
         "eligible_countries": countries,
+        "eligibility_known": eligibility_known,
         "topics": get_topics(card),
-        "project_code": (project_code or ""),
+        "project_code": (
+            project_code
+            or ""
+        ),
         "created": opportunity.get(
             "created",
             "",
         ),
-        "image_url": get_image_url(soup),
-        "url": (f"{BASE_URL}/solidarity/" f"opportunity/" f"{opportunity['opid']}_en"),
+        "image_url": get_image_url(
+            soup,
+        ),
+        "url": (
+            f"{BASE_URL}/solidarity/"
+            f"opportunity/"
+            f"{opportunity['opid']}_en"
+        ),
     }
 
     return {
-        "status": "match",
+        "status": "scanned",
         "result": result,
     }
 
 
+
 # ============================================================
 # ARCHIVE HELPERS
 # ============================================================
@@ -1099,26 +1153,37 @@ def archive_disappeared_matches(
     history: dict,
     current_ids: set[str],
 ) -> int:
-
     archived_count = 0
 
     for opid, entry in processed.items():
-
-        if entry.get("status") != "match":
+        if entry.get(
+            "status",
+        ) not in {
+            "match",
+            "scanned",
+            "error",
+            "parse_error",
+            "timeout",
+            "not_found",
+        }:
             continue
 
-        result = entry.get("result")
+        result = entry.get(
+            "result",
+        )
 
         if not result:
             continue
 
         if opid not in current_ids:
-
             archive_match(
                 history,
                 opid,
                 result,
-                ("No longer present in " "the active opportunity list."),
+                (
+                    "No longer present in "
+                    "the active opportunity list."
+                ),
             )
 
             archived_count += 1
@@ -1126,20 +1191,27 @@ def archive_disappeared_matches(
     return archived_count
 
 
+
 def archive_previous_match(
     history: dict,
     opid: str,
     previous_entry: dict | None,
     reason: str,
 ) -> bool:
-
     if not previous_entry:
         return False
 
-    if previous_entry.get("status") != "match":
+    if previous_entry.get(
+        "status",
+    ) not in {
+        "match",
+        "scanned",
+    }:
         return False
 
-    result = previous_entry.get("result")
+    result = previous_entry.get(
+        "result",
+    )
 
     if not result:
         return False
@@ -1154,6 +1226,7 @@ def archive_previous_match(
     return True
 
 
+
 # ============================================================
 # PUBLIC OUTPUT
 # ============================================================
@@ -1163,53 +1236,98 @@ def get_current_matches(
     checkpoint: dict,
     current_ids: set[str],
 ) -> list[dict]:
-
     processed = checkpoint.get(
         "processed",
         {},
     )
 
-    matches = []
+    opportunities = []
 
     for opid in current_ids:
-
-        entry = processed.get(opid)
+        entry = processed.get(
+            opid,
+        )
 
         if not entry:
             continue
 
-        if entry.get("status") != "match":
+        status = entry.get(
+            "status",
+        )
+
+        if status in {
+            "expired_deadline",
+            "activity_finished",
+        }:
             continue
 
-        result = entry.get("result")
+        result = entry.get(
+            "result",
+        )
 
         if result:
+            opportunities.append(
+                result,
+            )
 
-            matches.append(result)
-
-    matches.sort(
+    opportunities.sort(
         key=lambda item: (
-            item.get("deadline") or "9999-12-31",
+            item.get(
+                "deadline"
+            ) or "9999-12-31",
             item.get(
                 "title",
                 "",
             ),
-        )
+        ),
     )
 
-    return matches
+    return opportunities
+
 
 
 def save_public_output(
-    matches: list[dict],
+    opportunities: list[dict],
+    migration_complete: bool,
+    current_ids: set[str],
+    checkpoint: dict,
 ) -> None:
+    participant_countries = (
+        get_participant_countries(
+            opportunities,
+        )
+    )
+
+    scanned_count = sum(
+        1
+        for opid in current_ids
+        if checkpoint.get(
+            "processed",
+            {},
+        ).get(
+            opid,
+            {},
+        ).get(
+            "status",
+        ) == "scanned"
+    )
 
     output = {
+        "schema_version": OUTPUT_SCHEMA_VERSION,
         "generated_at": now_iso(),
-        "source_date": TODAY.strftime("%Y-%m-%d"),
-        "country": TARGET_COUNTRY,
-        "count": len(matches),
-        "opportunities": matches,
+        "source_date": TODAY.strftime(
+            "%Y-%m-%d",
+        ),
+        "count": len(
+            opportunities,
+        ),
+        "scanned_count": scanned_count,
+        "total_current": len(
+            current_ids,
+        ),
+        "migration_complete": migration_complete,
+        "participant_countries": participant_countries,
+        "opportunities": opportunities,
     }
 
     atomic_write_json(
@@ -1218,6 +1336,7 @@ def save_public_output(
     )
 
 
+
 def save_expired_output(
     history: dict,
 ) -> None:
@@ -1263,35 +1382,145 @@ def save_expired_output(
     )
 
 
-# ============================================================
-# WORK QUEUE
-# ============================================================
 
+def normalize_checkpoint_for_country_neutral_mode(
+    checkpoint: dict,
+) -> dict:
+    """
+    Migrate the old Morocco-specific checkpoint in place.
 
-def build_work_queue(
-    current_opportunities: list[dict],
+    Existing scanned opportunities already contain complete detail results,
+    including eligible_countries, so they can safely become generic
+    'scanned' records.
+
+    Legacy unscanned records with no result remain unresolved and are
+    deliberately queued for the one-time migration scan.
+    """
+
+    checkpoint.setdefault(
+        "schema_version",
+        1,
+    )
+
+    processed = checkpoint.get(
+        "processed",
+        {},
+    )
+
+    for entry in processed.values():
+        if (
+            entry.get("status") == "match"
+            and entry.get("result")
+        ):
+            entry["status"] = "scanned"
+
+    checkpoint["schema_version"] = CHECKPOINT_SCHEMA_VERSION
+
+    return checkpoint
+
+
+def is_entry_stale(
+    entry: dict,
+) -> bool:
+    checked_at = parse_iso_datetime(
+        entry.get("checked_at"),
+    )
+
+    if checked_at is None:
+        return True
+
+    age_seconds = (
+        datetime.now() - checked_at
+    ).total_seconds()
+
+    return age_seconds >= DETAIL_RECHECK_INTERVAL
+
+
+def migration_entry_complete(
+    entry: dict | None,
+) -> bool:
+    if not entry:
+        return False
+
+    status = entry.get(
+        "status",
+    )
+
+    if status == "scanned" and entry.get(
+        "result",
+    ):
+        return True
+
+    return status in {
+        "expired_deadline",
+        "activity_finished",
+        "not_found",
+    }
+
+
+def is_country_neutral_scan_complete(
     checkpoint: dict,
+    current_ids: set[str],
+) -> bool:
+    processed = checkpoint.get(
+        "processed",
+        {},
+    )
+
+    return all(
+        migration_entry_complete(
+            processed.get(opid),
+        )
+        for opid in current_ids
+    )
+
+
+def get_participant_countries(
+    opportunities: list[dict],
 ) -> list[str]:
-    """
-    Queue rules:
+    countries = {}
 
-    1. New opportunities:
-       Never seen before → scan.
+    for opportunity in opportunities:
+        for country in opportunity.get(
+            "eligible_countries",
+            [],
+        ):
+            value = str(
+                country
+            ).strip()
 
-    2. Technical failures:
-       Retry.
+            if not value:
+                continue
+
+            countries.setdefault(
+                value.casefold(),
+                value,
+            )
 
-    3. Existing Morocco matches:
-       Recheck every run.
+    return sorted(
+        countries.values(),
+        key=lambda value: value.casefold(),
+    )
 
-    4. Previously scanned non-Morocco opportunities:
-       Skip.
+# ============================================================
+# WORK QUEUE
+# ============================================================
 
-    5. Archived opportunities that disappeared:
-       Skip.
 
-    This is what allows the initial ~1200 opportunity scan
-    to eventually turn into a very small daily workload.
+def build_work_queue(
+    current_opportunities: list[dict],
+    checkpoint: dict,
+) -> list[str]:
+    """
+    Queue policy for the country-neutral dataset.
+
+    1. New opportunities are scanned immediately.
+    2. Legacy records without a complete result are scanned during
+       the one-time migration.
+    3. Technical failures are retried.
+    4. Active opportunities are periodically rechecked after the
+       configured stale interval.
+    5. Recently checked opportunities are skipped.
     """
 
     processed = checkpoint.get(
@@ -1299,64 +1528,107 @@ def build_work_queue(
         {},
     )
 
-    ordered_ids = [str(opportunity["opid"]) for opportunity in current_opportunities]
+    ordered_ids = [
+        str(
+            opportunity["opid"]
+        )
+        for opportunity in current_opportunities
+    ]
 
     new_ids = []
+    migration_ids = []
     retry_ids = []
-    match_ids = []
+    stale_ids = []
 
     for opid in ordered_ids:
-
-        entry = processed.get(opid)
-
-        # ----------------------------------------------------
-        # New opportunity.
-        # ----------------------------------------------------
+        entry = processed.get(
+            opid,
+        )
 
         if entry is None:
-
-            new_ids.append(opid)
-
+            new_ids.append(
+                opid,
+            )
             continue
 
-        status = entry.get("status")
+        status = entry.get(
+            "status",
+        )
 
-        # ----------------------------------------------------
-        # Retry technical problems.
-        # ----------------------------------------------------
+        result = entry.get(
+            "result",
+        )
 
+        # Legacy Morocco-specific entries with no result.
+        if (
+            not result
+            and status in {
+                "not_morocco",
+                "not_found",
+            }
+        ):
+            migration_ids.append(
+                opid,
+            )
+            continue
+
+        # Technical failures always get retried.
         if status in {
             "error",
             "parse_error",
             "timeout",
         }:
-
-            retry_ids.append(opid)
-
+            retry_ids.append(
+                opid,
+            )
             continue
 
-        # ----------------------------------------------------
-        # EXISTING MOROCCO MATCH.
-        #
-        # Recheck every run.
-        # ----------------------------------------------------
-
-        if status == "match":
+        # Entries which did not produce an active result are retried
+        # when they become stale.
+        if (
+            status in {
+                "expired_deadline",
+                "activity_finished",
+                "not_found",
+            }
+            and is_entry_stale(
+                entry,
+            )
+        ):
+            stale_ids.append(
+                opid,
+            )
+            continue
 
-            match_ids.append(opid)
+        # Every successfully scanned opportunity is periodically
+        # refreshed so participant eligibility changes are captured.
+        if status in {
+            "scanned",
+            "match",
+        }:
+            if is_entry_stale(
+                entry,
+            ):
+                stale_ids.append(
+                    opid,
+                )
 
             continue
 
-        # ----------------------------------------------------
-        # not_morocco
-        # not_found
-        # expired_deadline
-        # activity_finished
-        #
-        # Intentionally skipped.
-        # ----------------------------------------------------
+        # Any legacy/unrecognized state without a usable result must
+        # be migrated.
+        if not result:
+            migration_ids.append(
+                opid,
+            )
+
+    return (
+        new_ids
+        + migration_ids
+        + retry_ids
+        + stale_ids
+    )
 
-    return new_ids + retry_ids + match_ids
 
 
 # ============================================================
@@ -1365,13 +1637,16 @@ def build_work_queue(
 
 
 def main() -> int:
-
     print("=" * 70)
-    print("EU SOLIDARITY CORPS — " "MOROCCO OPPORTUNITY FINDER")
+    print(
+        "EUROPEAN SOLIDARITY CORPS — "
+        "OPPORTUNITY FINDER"
+    )
     print("=" * 70)
 
     print(
-        f"Date: " f"{TODAY.strftime('%d/%m/%Y')}",
+        f"Date: "
+        f"{TODAY.strftime('%d/%m/%Y')}",
         flush=True,
     )
 
@@ -1381,62 +1656,86 @@ def main() -> int:
     )
 
     print(
-        f"Detail request delay: " f"{DETAIL_REQUEST_DELAY}s",
+        f"Detail request delay: "
+        f"{DETAIL_REQUEST_DELAY}s",
         flush=True,
     )
 
     # --------------------------------------------------------
-    # 1. Fetch a fresh API snapshot.
+    # 1. Fresh active API snapshot.
     # --------------------------------------------------------
 
-    current_opportunities = fetch_current_opportunities()
+    current_opportunities = (
+        fetch_current_opportunities()
+    )
 
     if not current_opportunities:
+        raise RuntimeError(
+            "No current opportunities retrieved."
+        )
 
-        raise RuntimeError("No current opportunities retrieved.")
-
-    current_ids = {str(opportunity["opid"]) for opportunity in current_opportunities}
+    current_ids = {
+        str(
+            opportunity["opid"]
+        )
+        for opportunity in current_opportunities
+    }
 
     opportunities_by_id = {
-        str(opportunity["opid"]): opportunity for opportunity in current_opportunities
+        str(
+            opportunity["opid"]
+        ): opportunity
+        for opportunity in current_opportunities
     }
 
     # --------------------------------------------------------
-    # 2. Load persistent state.
+    # 2. Persistent migration-aware checkpoint.
     # --------------------------------------------------------
 
     checkpoint = load_checkpoint()
 
-    processed = checkpoint["processed"]
+    processed = checkpoint[
+        "processed"
+    ]
 
-    history = checkpoint["history"]
+    history = checkpoint[
+        "history"
+    ]
+
+    migration_complete = (
+        is_country_neutral_scan_complete(
+            checkpoint,
+            current_ids,
+        )
+    )
 
     # --------------------------------------------------------
-    # 3. Archive Morocco matches that disappeared from the
-    #    active API.
+    # 3. Archive active opportunities which disappeared from
+    #    the API.
     # --------------------------------------------------------
 
-    disappeared_count = archive_disappeared_matches(
-        processed,
-        history,
-        current_ids,
+    disappeared_count = (
+        archive_disappeared_matches(
+            processed,
+            history,
+            current_ids,
+        )
     )
 
     if disappeared_count:
-
         print(
-            f"Archived "
-            f"{disappeared_count} "
-            f"opportunity/opportunities "
-            f"that disappeared from "
-            f"the active list.",
+            f"Archived {disappeared_count} "
+            "opportunity/opportunities that "
+            "disappeared from the active list.",
             flush=True,
         )
 
-        save_checkpoint(checkpoint)
+        save_checkpoint(
+            checkpoint,
+        )
 
     # --------------------------------------------------------
-    # 4. Build current work queue.
+    # 4. Work queue.
     # --------------------------------------------------------
 
     queue = build_work_queue(
@@ -1444,108 +1743,141 @@ def main() -> int:
         checkpoint,
     )
 
-    already_processed = sum(1 for opid in current_ids if opid in processed)
-
-    new_count = sum(1 for opid in current_ids if opid not in processed)
-
-    existing_match_count = sum(
-        1 for opid in current_ids if (processed.get(opid, {}).get("status") == "match")
+    already_processed = sum(
+        1
+        for opid in current_ids
+        if opid in processed
     )
 
-    batch = queue[:BATCH_SIZE]
+    batch = queue[
+        :BATCH_SIZE
+    ]
 
-    # --------------------------------------------------------
-    # 5. Print plan.
-    # --------------------------------------------------------
-
-    print("\n")
+    print()
     print("=" * 70)
     print("SCAN PLAN")
     print("=" * 70)
 
-    print(f"Current opportunities: " f"{len(current_opportunities)}")
-
-    print(f"Already processed: " f"{already_processed}")
+    print(
+        f"Current opportunities: "
+        f"{len(current_opportunities)}"
+    )
 
-    print(f"New opportunities: " f"{new_count}")
+    print(
+        f"Already processed: "
+        f"{already_processed}"
+    )
 
-    print(f"Existing Morocco matches: " f"{existing_match_count}")
+    print(
+        f"Country-neutral scan complete: "
+        f"{migration_complete}"
+    )
 
-    print(f"Work remaining: " f"{len(queue)}")
+    print(
+        f"Work remaining: "
+        f"{len(queue)}"
+    )
 
-    print(f"This batch: " f"{len(batch)}")
+    print(
+        f"This batch: "
+        f"{len(batch)}"
+    )
 
     print("=" * 70)
 
     # --------------------------------------------------------
-    # 6. Nothing to scan.
+    # 5. Nothing to scan.
     # --------------------------------------------------------
 
     if not batch:
-
-        current_matches = get_current_matches(
+        opportunities = get_current_matches(
             checkpoint,
             current_ids,
         )
 
-        save_public_output(current_matches)
+        migration_complete = (
+            is_country_neutral_scan_complete(
+                checkpoint,
+                current_ids,
+            )
+        )
 
-        save_expired_output(history)
+        save_public_output(
+            opportunities,
+            migration_complete,
+            current_ids,
+            checkpoint,
+        )
 
-        save_checkpoint(checkpoint)
+        save_expired_output(
+            history,
+        )
+
+        save_checkpoint(
+            checkpoint,
+        )
 
         print(
-            "\n" "NO DETAIL SCANNING REQUIRED",
+            "\nNO DETAIL SCANNING REQUIRED",
             flush=True,
         )
 
         print(
-            f"Current Morocco matches: " f"{len(current_matches)}",
+            f"Current published opportunities: "
+            f"{len(opportunities)}",
             flush=True,
         )
 
         print(
-            "All current non-Morocco "
-            "opportunities are already "
-            "known and are being skipped.",
+            f"Country-neutral migration complete: "
+            f"{migration_complete}",
             flush=True,
         )
 
         return 0
 
     # --------------------------------------------------------
-    # 7. Cooldown before detail scanning.
+    # 6. Cooldown.
     # --------------------------------------------------------
 
     print(
-        f"\nWaiting " f"{DETAIL_SCAN_COOLDOWN}s " f"before detail scanning...",
+        f"\nWaiting "
+        f"{DETAIL_SCAN_COOLDOWN}s "
+        "before detail scanning...",
         flush=True,
     )
 
-    time.sleep(DETAIL_SCAN_COOLDOWN)
+    time.sleep(
+        DETAIL_SCAN_COOLDOWN,
+    )
 
     # --------------------------------------------------------
-    # 8. Process this batch.
+    # 7. Process batch.
     # --------------------------------------------------------
 
     session = requests.Session()
 
     processed_this_batch = 0
-    new_matches = 0
+    scanned_this_batch = 0
     archived_this_batch = 0
-
     rate_limited = False
 
     try:
-
         for index, opid in enumerate(
             batch,
             start=1,
         ):
+            opportunity = (
+                opportunities_by_id[
+                    opid
+                ]
+            )
 
-            opportunity = opportunities_by_id[opid]
-
-            previous_entry = processed.get(opid)
+            previous_entry = (
+                processed.get(
+                    opid,
+                )
+            )
 
             print(
                 "\n" + "=" * 60,
@@ -1553,21 +1885,19 @@ def main() -> int:
             )
 
             print(
-                f"[{index}/{len(batch)}] " f"Checking ID {opid}",
+                f"[{index}/{len(batch)}] "
+                f"Checking ID {opid}",
                 flush=True,
             )
 
-            status, html = fetch_detail_page(
-                session,
-                opportunity,
+            status, html = (
+                fetch_detail_page(
+                    session,
+                    opportunity,
+                )
             )
 
-            # ------------------------------------------------
-            # RATE LIMIT
-            # ------------------------------------------------
-
             if status == "429":
-
                 rate_limited = True
 
                 print(
@@ -1591,183 +1921,184 @@ def main() -> int:
 
             checked_at = now_iso()
 
-            # ------------------------------------------------
-            # 404
-            # ------------------------------------------------
-
             if status == "404":
-
+                # Preserve the last known result when available. The
+                # active API still lists this opportunity, so a 404
+                # can be transient.
                 processed[opid] = {
                     "status": "not_found",
-                    "result": None,
+                    "result": (
+                        previous_entry.get(
+                            "result"
+                        )
+                        if previous_entry
+                        else None
+                    ),
                     "checked_at": checked_at,
                 }
 
-            # ------------------------------------------------
-            # Technical error
-            # ------------------------------------------------
-
             elif status != "200":
-
                 processed[opid] = {
                     "status": "error",
                     "http_status": status,
-                    "result": None,
+                    "result": (
+                        previous_entry.get(
+                            "result"
+                        )
+                        if previous_entry
+                        else None
+                    ),
                     "checked_at": checked_at,
                 }
 
-            # ------------------------------------------------
-            # Successful page
-            # ------------------------------------------------
-
             else:
-
                 parsed = parse_detail_page(
                     opportunity,
                     html,
                 )
 
-                new_status = parsed.get("status")
-
-                # --------------------------------------------
-                # A previous Morocco match stopped qualifying.
-                # Archive the previous result before replacing
-                # the checkpoint entry.
-                # --------------------------------------------
+                new_status = parsed.get(
+                    "status",
+                )
 
+                # If a previously valid active result has actually
+                # expired or finished, archive it before removing it
+                # from the active dataset.
                 if (
                     previous_entry
-                    and previous_entry.get("status") == "match"
-                    and new_status != "match"
+                    and previous_entry.get(
+                        "status",
+                    ) in {
+                        "match",
+                        "scanned",
+                    }
+                    and previous_entry.get(
+                        "result",
+                    )
+                    and new_status in {
+                        "expired_deadline",
+                        "activity_finished",
+                    }
                 ):
+                    reason = (
+                        "Application deadline has expired."
+                        if new_status
+                        == "expired_deadline"
+                        else
+                        "Activity has finished."
+                    )
 
-                    if new_status == "not_morocco":
-
-                        if archive_previous_match(
-                            history,
-                            opid,
-                            previous_entry,
-                            (
-                                "No longer lists "
-                                "Morocco among the "
-                                "eligible participant "
-                                "countries."
-                            ),
-                        ):
-
-                            archived_this_batch += 1
-
-                    elif new_status == "expired_deadline":
-
-                        if archive_previous_match(
-                            history,
-                            opid,
-                            previous_entry,
-                            ("Application deadline " "has expired."),
-                        ):
-
-                            archived_this_batch += 1
-
-                    elif new_status == "activity_finished":
-
-                        if archive_previous_match(
-                            history,
-                            opid,
-                            previous_entry,
-                            ("Activity has finished."),
-                        ):
-
-                            archived_this_batch += 1
-
-                # --------------------------------------------
-                # A previously archived opportunity has become
-                # active again and is now a Morocco match.
-                # Remove its archive entry.
-                # --------------------------------------------
-
-                if new_status == "match":
+                    if archive_previous_match(
+                        history,
+                        opid,
+                        previous_entry,
+                        reason,
+                    ):
+                        archived_this_batch += 1
 
+                if new_status == "scanned":
                     if opid in history:
-
                         del history[opid]
 
-                    new_matches += 1
-
-                    result = parsed["result"]
+                    scanned_this_batch += 1
 
-                    print(
-                        "\n✅ MOROCCO MATCH",
-                        flush=True,
+                    result = parsed.get(
+                        "result",
                     )
 
-                    print(
-                        f"{result['id']} — " f"{result['title']}",
-                        flush=True,
-                    )
-
-                    print(
-                        f"Activity: "
-                        f"{result['start_date']} "
-                        f"→ "
-                        f"{result['end_date']}",
-                        flush=True,
-                    )
-
-                    print(
-                        f"Deadline: " f"{result['deadline'] or 'No deadline'}",
-                        flush=True,
-                    )
+                    if result:
+                        print(
+                            "\n✅ OPPORTUNITY SCANNED",
+                            flush=True,
+                        )
+
+                        print(
+                            f"{result['id']} — "
+                            f"{result['title']}",
+                            flush=True,
+                        )
+
+                elif new_status in {
+                    "parse_error",
+                }:
+                    # Preserve a last known result while requiring a
+                    # future successful scan before migration is called
+                    # complete.
+                    if (
+                        previous_entry
+                        and previous_entry.get(
+                            "result",
+                        )
+                    ):
+                        parsed[
+                            "result"
+                        ] = previous_entry[
+                            "result"
+                        ]
 
                 processed[opid] = {
                     **parsed,
                     "checked_at": checked_at,
                 }
 
-            # ------------------------------------------------
-            # SAVE CHECKPOINT AFTER EVERY SUCCESSFULLY
-            # HANDLED DETAIL PAGE.
-            # ------------------------------------------------
-
-            checkpoint["processed"] = processed
+            checkpoint[
+                "processed"
+            ] = processed
 
-            checkpoint["history"] = history
+            checkpoint[
+                "history"
+            ] = history
 
-            save_checkpoint(checkpoint)
+            save_checkpoint(
+                checkpoint,
+            )
 
             print(
-                f"Checkpoint saved " f"after ID {opid}.",
+                f"Checkpoint saved after ID {opid}.",
                 flush=True,
             )
 
-            # ------------------------------------------------
-            # Rate-limit-friendly delay.
-            # ------------------------------------------------
-
             if index < len(batch):
-
-                time.sleep(DETAIL_REQUEST_DELAY)
+                time.sleep(
+                    DETAIL_REQUEST_DELAY,
+                )
 
     finally:
-
         session.close()
 
     # --------------------------------------------------------
-    # 9. Build the current public dataset.
+    # 8. Build current country-neutral output.
     # --------------------------------------------------------
 
-    current_matches = get_current_matches(
+    opportunities = get_current_matches(
         checkpoint,
         current_ids,
     )
 
-    save_public_output(current_matches)
+    migration_complete = (
+        is_country_neutral_scan_complete(
+            checkpoint,
+            current_ids,
+        )
+    )
 
-    save_expired_output(history)
+    save_public_output(
+        opportunities,
+        migration_complete,
+        current_ids,
+        checkpoint,
+    )
 
-    save_checkpoint(checkpoint)
+    save_expired_output(
+        history,
+    )
+
+    save_checkpoint(
+        checkpoint,
+    )
 
     # --------------------------------------------------------
-    # 10. See what remains.
+    # 9. Remaining queue.
     # --------------------------------------------------------
 
     remaining_queue = build_work_queue(
@@ -1775,78 +2106,80 @@ def main() -> int:
         checkpoint,
     )
 
-    # --------------------------------------------------------
-    # 11. Summary.
-    # --------------------------------------------------------
-
-    print("\n")
+    print()
     print("=" * 70)
     print("BATCH COMPLETE")
     print("=" * 70)
 
-    print(f"Processed this batch: " f"{processed_this_batch}")
+    print(
+        f"Processed this batch: "
+        f"{processed_this_batch}"
+    )
+
+    print(
+        f"Successfully scanned: "
+        f"{scanned_this_batch}"
+    )
 
-    print(f"Morocco matches found/rechecked: " f"{new_matches}")
+    print(
+        f"Archived this batch: "
+        f"{archived_this_batch}"
+    )
 
-    print(f"Archived this batch: " f"{archived_this_batch}")
+    print(
+        f"Current country-neutral opportunities: "
+        f"{len(opportunities)}"
+    )
 
-    print(f"Current Morocco matches: " f"{len(current_matches)}")
+    print(
+        f"Remaining work: "
+        f"{len(remaining_queue)}"
+    )
 
-    print(f"Remaining work: " f"{len(remaining_queue)}")
+    print(
+        f"Country-neutral migration complete: "
+        f"{migration_complete}"
+    )
 
     print("=" * 70)
 
-    # --------------------------------------------------------
-    # 12. Rate-limit result.
-    # --------------------------------------------------------
-
     if rate_limited:
-
         print(
-            "⚠️ Rate limited. " "Checkpoint saved.",
+            "⚠️ Rate limited. "
+            "Checkpoint saved.",
             flush=True,
         )
 
         print(
-            "The next run will resume " "from the checkpoint.",
+            "The next workflow run will resume.",
             flush=True,
         )
 
         return 2
 
-    # --------------------------------------------------------
-    # 13. Normal batch result.
-    # --------------------------------------------------------
-
     if remaining_queue:
-
         print(
-            "More opportunities remain " "to be processed.",
+            "More opportunities remain "
+            "to be processed.",
             flush=True,
         )
 
         print(
-            "The next workflow run " "will continue.",
+            "The next batch will continue "
+            "from the checkpoint.",
             flush=True,
         )
 
     else:
-
         print(
-            "🎉 Initial population scan " "is complete.",
-            flush=True,
-        )
-
-        print(
-            "Future runs should only "
-            "process new opportunities "
-            "and current Morocco matches.",
+            "🎉 Country-neutral scan is complete.",
             flush=True,
         )
 
     return 0
 
 
+
 # ============================================================
 # ENTRY POINT
 # ============================================================
diff --git a/web/app.js b/web/app.js
index 430a5a1..4e00cb3 100644
--- a/web/app.js
+++ b/web/app.js
@@ -60,16 +60,13 @@ const refreshButton = document.getElementById("refresh-button");
 const translations = {
   en: {
     title: "ESC Opportunity Finder",
-
     subtitle: "Find European Solidarity Corps volunteering opportunities open to participants from your country",
-
     activeOpportunities: "Active opportunities",
 
     lastUpdated: "Last updated",
 
     intro:
       "Find active European Solidarity Corps volunteering opportunities open to participants from your country.",
-
     introNote:
       "The list is automatically refreshed from the European Youth Portal.",
 
@@ -159,19 +156,20 @@ const translations = {
 
      darkMode: "Dark mode",
   },
+    participantCountry: "Participant country",
+    selectParticipantCountry: "Select participant country",
+    apply: "Apply",
+    allParticipantCountries: "All participant countries",
 
   fr: {
     title: "Outil de recherche d’opportunités du CES",
-
     subtitle: "Trouvez des opportunités de volontariat du Corps européen de solidarité ouvertes aux participants de votre pays",
-
     activeOpportunities: "Opportunités actives",
 
     lastUpdated: "Dernière mise à jour",
 
     intro:
       "Voici les opportunités de volontariat actives du Corps européen de solidarité ouvertes aux participants de votre pays.",
-
     introNote:
       "La liste est automatiquement actualisée depuis le Portail européen de la jeunesse.",
 
@@ -262,19 +260,20 @@ const translations = {
 
      darkMode: "Mode sombre",
   },
+    participantCountry: "Pays du participant",
+    selectParticipantCountry: "Sélectionnez le pays du participant",
+    apply: "Appliquer",
+    allParticipantCountries: "Tous les pays participants",
 
   ar: {
     title: "البحث عن فرص الفيلق الأوروبي للتضامن",
-
     subtitle: "ابحث عن فرص التطوع ضمن الفيلق الأوروبي للتضامن المفتوحة للمشاركين من بلدك",
-
     activeOpportunities: "الفرص المتاحة",
 
     lastUpdated: "آخر تحديث",
 
     intro:
       "هذه هي فرص التطوع النشطة ضمن الفيلق الأوروبي للتضامن المفتوحة للمشاركين من بلدك.",
-
     introNote: "يتم تحديث القائمة تلقائياً من بوابة الشباب الأوروبية.",
 
     search: "بحث",
@@ -400,6 +399,10 @@ function applyTranslations() {
 
   populateFilters();
 
+  if (currentActiveData) {
+    populateParticipantCountries(currentActiveData);
+  }
+
   renderActive();
 
   renderExpired();
@@ -1291,6 +1294,11 @@ const topicIcons = {
   "Post Disaster relief": "🆘",
 
   "WASH (Water, sanitation and hygiene)": "🚿",
+    participantCountry: "بلد المشارك",
+    selectParticipantCountry: "اختر بلد المشارك",
+    apply: "تطبيق",
+    allParticipantCountries: "جميع بلدان المشاركين",
+
 };
 
 function renderTopics(topics) {
@@ -1331,6 +1339,178 @@ function renderTopics(topics) {
     `;
 }
 
+
+// ============================================================
+// PARTICIPANT COUNTRY FILTER
+// ============================================================
+
+const PARTICIPANT_COUNTRY_STORAGE_KEY =
+  "esc_participant_country";
+
+const participantCountryFilter =
+  document.getElementById(
+    "participant-country",
+  );
+
+const applyParticipantCountryButton =
+  document.getElementById(
+    "apply-participant-country",
+  );
+
+let selectedParticipantCountry =
+  localStorage.getItem(
+    PARTICIPANT_COUNTRY_STORAGE_KEY,
+  ) || "";
+
+let participantCountryDraft =
+  selectedParticipantCountry;
+
+function normalizeParticipantCountry(value) {
+  return String(value || "")
+    .trim()
+    .toLocaleLowerCase();
+}
+
+function getParticipantCountries(data) {
+  if (
+    Array.isArray(
+      data?.participant_countries,
+    )
+  ) {
+    return [...data.participant_countries]
+      .filter(Boolean)
+      .sort((a, b) =>
+        String(a).localeCompare(
+          String(b),
+          currentLanguage === "fr"
+            ? "fr"
+            : currentLanguage === "ar"
+              ? "ar"
+              : "en",
+        )
+      );
+  }
+
+  const derived =
+    activeOpportunities.flatMap(
+      (opportunity) =>
+        Array.isArray(
+          opportunity.eligible_countries,
+        )
+          ? opportunity.eligible_countries
+          : [],
+    );
+
+  return [
+    ...new Set(
+      derived
+        .map((country) =>
+          String(country).trim()
+        )
+        .filter(Boolean),
+    ),
+  ].sort((a, b) =>
+    String(a).localeCompare(
+      String(b),
+      currentLanguage === "fr"
+        ? "fr"
+        : currentLanguage === "ar"
+          ? "ar"
+          : "en",
+    )
+  );
+}
+
+function populateParticipantCountries(data) {
+  if (!participantCountryFilter) {
+    return;
+  }
+
+  const countries =
+    getParticipantCountries(data);
+
+  participantCountryFilter.innerHTML = "";
+
+  const placeholder =
+    document.createElement("option");
+
+  placeholder.value = "";
+  placeholder.textContent =
+    t("selectParticipantCountry");
+
+  participantCountryFilter.appendChild(
+    placeholder,
+  );
+
+  countries.forEach((country) => {
+    const option =
+      document.createElement("option");
+
+    option.value = country;
+    option.textContent = country;
+
+    participantCountryFilter.appendChild(
+      option,
+    );
+  });
+
+  const saved =
+    countries.find(
+      (country) =>
+        normalizeParticipantCountry(
+          country,
+        ) ===
+        normalizeParticipantCountry(
+          participantCountryDraft,
+        ),
+    );
+
+  participantCountryFilter.value =
+    saved || "";
+}
+
+function applyParticipantCountry() {
+  if (!participantCountryFilter) {
+    return;
+  }
+
+  selectedParticipantCountry =
+    participantCountryFilter.value;
+
+  participantCountryDraft =
+    selectedParticipantCountry;
+
+  if (selectedParticipantCountry) {
+    localStorage.setItem(
+      PARTICIPANT_COUNTRY_STORAGE_KEY,
+      selectedParticipantCountry,
+    );
+  } else {
+    localStorage.removeItem(
+      PARTICIPANT_COUNTRY_STORAGE_KEY,
+    );
+  }
+
+  renderActive();
+}
+
+if (participantCountryFilter) {
+  participantCountryFilter.addEventListener(
+    "change",
+    () => {
+      participantCountryDraft =
+        participantCountryFilter.value;
+    },
+  );
+}
+
+if (applyParticipantCountryButton) {
+  applyParticipantCountryButton.addEventListener(
+    "click",
+    applyParticipantCountry,
+  );
+}
+
 // ============================================================
 // FILTER OPTIONS
 // ============================================================
@@ -1424,6 +1604,27 @@ function getFilteredActive() {
       return false;
     }
 
+    if (
+      selectedParticipantCountry &&
+      !(
+        Array.isArray(
+          opportunity.eligible_countries,
+        ) &&
+        opportunity.eligible_countries.some(
+          (country) =>
+            normalizeParticipantCountry(
+              country,
+            ) ===
+            normalizeParticipantCountry(
+              selectedParticipantCountry,
+            ),
+        )
+      )
+    ) {
+      return false;
+    }
+
+
     if (type && opportunity.activity_type !== type) {
       return false;
     }
@@ -1519,6 +1720,11 @@ function sortOpportunities(items) {
 function renderActive() {
   const filtered = sortOpportunities(getFilteredActive());
 
+  opportunityCount.textContent =
+    filtered.length === 1
+      ? `1 ${t("result")}`
+      : `${filtered.length} ${t("results")}`;
+
   activeResultCount.textContent =
     `${filtered.length} ` +
     (filtered.length === 1 ? t("result") : t("results"));
@@ -1837,6 +2043,8 @@ async function loadData() {
 
     populateFilters();
 
+    populateParticipantCountries(currentActiveData);
+
     updateHeader(currentActiveData);
 
     renderActive();
diff --git a/web/index.html b/web/index.html
index c1c56ab..118c696 100644
--- a/web/index.html
+++ b/web/index.html
@@ -12,7 +12,7 @@
       content="Find European Solidarity Corps volunteering opportunities open to participants from your country."
     />
 
-    <link rel="stylesheet" href="style.css?v=4" />
+    <link rel="stylesheet" href="style.css?v=8" />
 
     <script>
       (() => {
@@ -200,7 +200,39 @@
         <p class="intro-note" data-i18n="introNote">
           The list is automatically refreshed from the European Youth Portal.
         </p>
-      </section>
+
+        <div class="participant-selector">
+          <div class="participant-selector-field">
+            <label
+              for="participant-country"
+              data-i18n="participantCountry"
+            >
+              Participant country
+            </label>
+
+            <select
+              id="participant-country"
+              autocomplete="country-name"
+            >
+              <option
+                value=""
+                data-i18n="selectParticipantCountry"
+              >
+                Select participant country
+              </option>
+            </select>
+          </div>
+
+          <button
+            id="apply-participant-country"
+            class="participant-apply-button"
+            type="button"
+            data-i18n="apply"
+          >
+            Apply
+          </button>
+        </div>
+</section>
 
       <!-- =====================================================
          CONTROLS
@@ -381,7 +413,7 @@
       </footer>
     </main>
 
-    <script src="app.js?v=12"></script>
+    <script src="app.js?v=16"></script>
   </body>
 </html>
 <!-- ESC-MOROCCO-PAGES-REDEPLOY -->
diff --git a/web/style.css b/web/style.css
index 0fd6329..a83bb6c 100644
--- a/web/style.css
+++ b/web/style.css
@@ -1487,3 +1487,126 @@ html[dir="rtl"] .language-dropdown-menu {
 html[dir="rtl"] .language-option {
   text-align: right;
 }
+
+
+/* ============================================================
+   PARTICIPANT COUNTRY SELECTOR
+   ============================================================ */
+
+.participant-selector {
+  display: flex;
+
+  align-items: flex-end;
+
+  gap: 14px;
+
+  margin-top: 18px;
+
+  padding: 16px;
+
+  border: 1px solid var(--border);
+
+  border-radius: 12px;
+
+  background: var(--surface);
+
+  box-shadow: var(--shadow);
+}
+
+.participant-selector-field {
+  display: flex;
+
+  flex: 1;
+
+  min-width: 0;
+
+  flex-direction: column;
+
+  gap: 7px;
+}
+
+.participant-selector-field label {
+  color: var(--text);
+
+  font-size: 0.85rem;
+
+  font-weight: 700;
+}
+
+#participant-country {
+  width: 100%;
+
+  min-height: 42px;
+
+  padding: 8px 12px;
+
+  border: 1px solid var(--border);
+
+  border-radius: 9px;
+
+  background: var(--surface);
+
+  color: var(--text);
+
+  font: inherit;
+
+  cursor: pointer;
+}
+
+#participant-country:focus-visible {
+  outline: 2px solid rgba(40, 85, 217, 0.3);
+
+  outline-offset: 2px;
+}
+
+.participant-apply-button {
+  min-height: 42px;
+
+  padding: 8px 20px;
+
+  border: 0;
+
+  border-radius: 9px;
+
+  background: var(--primary);
+
+  color: white;
+
+  font: inherit;
+
+  font-weight: 700;
+
+  cursor: pointer;
+
+  transition:
+    background 0.15s ease,
+    transform 0.1s ease;
+}
+
+.participant-apply-button:hover {
+  background: var(--primary-dark);
+}
+
+.participant-apply-button:active {
+  transform: translateY(1px);
+}
+
+html[dir="rtl"] .participant-selector {
+  flex-direction: row-reverse;
+}
+
+@media (max-width: 640px) {
+  .participant-selector {
+    flex-direction: column;
+
+    align-items: stretch;
+  }
+
+  html[dir="rtl"] .participant-selector {
+    flex-direction: column;
+  }
+
+  .participant-apply-button {
+    width: 100%;
+  }
+}
```

No commit or push was performed.
