import json
import tempfile
from pathlib import Path

from scraper import (
    archive_disappeared_matches,
    archive_previous_match,
    save_expired_output,
)


def print_json(title, data):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main():
    # ========================================================
    # TEST DATA
    # ========================================================

    fake_match = {
        "id": 99999,
        "title": "TEST — Morocco Eligible Opportunity",
        "location": "Test City",
        "country": "DE",
        "town": "Test City",
        "activity_type": "Individual volunteering",
        "start_date": "2026-09-01",
        "end_date": "2027-03-01",
        "deadline": "2026-08-30",
        "eligible_countries": [
            "Morocco",
            "France",
            "Germany",
        ],
        "topics": [
            "Education and training"
        ],
        "project_code": "TEST-99999",
        "created": "2026-08-01T12:00:00",
        "url": (
            "https://youth.europa.eu/"
            "solidarity/opportunity/99999_en"
        ),
    }


    # ========================================================
    # TEST 1
    #
    # Previously matched opportunity disappears from the
    # active API list.
    # ========================================================

    processed = {
        "99999": {
            "status": "match",
            "result": fake_match,
            "checked_at": "2026-08-14T10:00:00",
        }
    }

    history = {}

    current_ids = set()

    archived_count = (
        archive_disappeared_matches(
            processed,
            history,
            current_ids,
        )
    )

    print(
        f"\nTest 1 — disappeared opportunity"
    )

    assert archived_count == 1, (
        "Expected exactly one archived opportunity."
    )

    assert "99999" in history, (
        "Opportunity should be present in history."
    )

    assert (
        history["99999"]["reason"]
        == (
            "No longer present in "
            "the active opportunity list."
        )
    ), "Incorrect archive reason."

    print("✅ Passed")


    # ========================================================
    # TEST 2
    #
    # Previously Morocco-eligible opportunity is still active
    # but no longer lists Morocco as an eligible country.
    # ========================================================

    history = {}

    previous_entry = {
        "status": "match",
        "result": fake_match,
        "checked_at": "2026-08-14T10:00:00",
    }

    archived = archive_previous_match(
        history,
        "99999",
        previous_entry,
        (
            "No longer lists Morocco among "
            "the eligible participant countries."
        ),
    )

    print(
        f"\nTest 2 — Morocco eligibility removed"
    )

    assert archived is True, (
        "Expected previous match to be archived."
    )

    assert "99999" in history, (
        "Opportunity should be present in history."
    )

    assert (
        history["99999"]["reason"]
        == (
            "No longer lists Morocco among "
            "the eligible participant countries."
        )
    ), "Incorrect eligibility archive reason."

    print("✅ Passed")


    # ========================================================
    # TEST 3
    #
    # Verify that archive records can be converted into the
    # same expired.json structure used by production.
    # ========================================================

    print(
        f"\nTest 3 — expired.json generation"
    )

    with tempfile.TemporaryDirectory() as temp_dir:

        temp_path = Path(temp_dir) / "expired.json"

        # Temporarily redirect the production output path.
        import scraper

        original_path = scraper.EXPIRED_FILE

        scraper.EXPIRED_FILE = temp_path

        try:

            save_expired_output(
                history
            )

        finally:

            scraper.EXPIRED_FILE = original_path


        assert temp_path.exists(), (
            "expired.json was not created."
        )

        with temp_path.open(
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)


        assert data["count"] == 1, (
            "Expected exactly one archived opportunity."
        )

        assert (
            data["opportunities"][0]["id"]
            == 99999
        ), "Archived opportunity ID is wrong."

        assert (
            data["opportunities"][0]["reason"]
            == (
                "No longer lists Morocco among "
                "the eligible participant countries."
            )
        ), "Archive reason was not preserved."

        print_json(
            "Generated expired.json",
            data,
        )

        print("✅ Passed")


    # ========================================================
    # FINAL
    # ========================================================

    print()
    print("=" * 70)
    print("ALL ARCHIVE TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()