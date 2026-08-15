import unittest

from .cache import (
    load_cache,
    load_participant_country_index,
    opportunity_matches_country,
    search_cache,
)


class CacheTests(unittest.TestCase):

    def test_cache_loads(self):
        data = load_cache()

        self.assertIsInstance(
            data,
            dict,
        )

        self.assertIsInstance(
            data.get("opportunities"),
            list,
        )

    def test_participant_country_index_loads(self):
        index = load_participant_country_index()

        self.assertIsInstance(
            index,
            dict,
        )

        self.assertIsInstance(
            index.get("countries"),
            dict,
        )

    def test_opportunity_country_matching(self):
        opportunity = {
            "id": "TEST-1",
            "eligible_countries": [
                "MA",
                "FR",
            ],
        }

        self.assertTrue(
            opportunity_matches_country(
                opportunity,
                "MA",
            )
        )

        self.assertTrue(
            opportunity_matches_country(
                opportunity,
                "FR",
            )
        )

        self.assertFalse(
            opportunity_matches_country(
                opportunity,
                "DE",
            )
        )

    def test_country_code_is_case_insensitive(self):
        opportunity = {
            "id": "TEST-2",
            "eligible_countries": [
                "MA",
            ],
        }

        self.assertTrue(
            opportunity_matches_country(
                opportunity,
                "ma",
            )
        )

    def test_invalid_country_is_rejected(self):
        with self.assertRaises(
            ValueError
        ):
            search_cache(
                "MOR"
            )

    def test_search_returns_expected_shape(self):
        payload = search_cache(
            "MA"
        )

        self.assertEqual(
            payload["status"],
            "success",
        )

        self.assertEqual(
            payload["participant_country"],
            "MA",
        )

        self.assertIsInstance(
            payload["count"],
            int,
        )

        self.assertIsInstance(
            payload["opportunities"],
            list,
        )

    def test_index_search_matches_direct_scan(self):
        data = load_cache()

        direct_matches = [
            opportunity
            for opportunity in data.get(
                "opportunities",
                [],
            )
            if opportunity_matches_country(
                opportunity,
                "MA",
            )
        ]

        indexed_result = search_cache(
            "MA"
        )

        self.assertEqual(
            len(direct_matches),
            indexed_result["count"],
        )

        direct_ids = {
            str(item["id"])
            for item in direct_matches
        }

        indexed_ids = {
            str(item["id"])
            for item in indexed_result["opportunities"]
        }

        self.assertEqual(
            direct_ids,
            indexed_ids,
        )

    def test_index_search_is_country_agnostic(self):
        index = load_participant_country_index()

        countries = index.get(
            "countries",
            {},
        )

        self.assertIn(
            "MA",
            countries,
        )

        self.assertGreater(
            len(countries),
            1,
        )

        for country_code in list(countries)[:3]:
            payload = search_cache(
                country_code
            )

            self.assertEqual(
                payload["status"],
                "success",
            )

            self.assertEqual(
                payload["participant_country"],
                country_code,
            )


if __name__ == "__main__":
    unittest.main()
