import unittest

from .cache import (
    opportunity_matches_country,
    search_country,
)


class CacheTests(unittest.TestCase):

    def test_cache_loads(self):
        results = search_country("MA")

        self.assertIsInstance(
            results,
            list,
        )

    def test_country_code_is_case_insensitive(self):
        opportunity = {
            "id": "test",
            "eligible_countries": [
                "MA",
                "FR",
            ],
        }

        self.assertTrue(
            opportunity_matches_country(
                opportunity,
                "ma",
            )
        )

        self.assertTrue(
            opportunity_matches_country(
                opportunity,
                " Ma ",
            )
        )

    def test_invalid_country_is_rejected(self):
        with self.assertRaises(ValueError):
            search_country("MOR")

    def test_opportunity_country_matching(self):
        opportunity = {
            "id": "test",
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

    def test_search_returns_expected_shape(self):
        results = search_country("MA")

        self.assertIsInstance(
            results,
            list,
        )

        for opportunity in results:
            self.assertIsInstance(
                opportunity,
                dict,
            )


if __name__ == "__main__":
    unittest.main()
