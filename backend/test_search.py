import unittest

from .cache import (
    load_cache,
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

    def test_search_returns_expected_shape(self):
        payload = search_cache("MA")

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


if __name__ == "__main__":
    unittest.main()
