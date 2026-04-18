import unittest

from app.models.domain_pattern import DomainPattern
from app.services.email_finder import infer_pattern, rank_candidates, _update_pattern_stats


class EmailFinderHelperTests(unittest.TestCase):
    def test_rank_candidates_prefers_higher_confidence_sources(self) -> None:
        ranked = rank_candidates(
            "Jane",
            "Doe",
            "example.com",
            exa_hits=["jane.doe@example.com"],
            firecrawl_hits=["jane.doe@example.com", "jdoe@example.com"],
            pattern_hits=[("jane.doe@example.com", 0.7), ("jdoe@example.com", 0.68)],
        )

        self.assertEqual(ranked[0].email, "jane.doe@example.com")
        self.assertEqual(ranked[0].reason_code, "exa_found")
        self.assertEqual(ranked[1].email, "jdoe@example.com")
        self.assertEqual(ranked[1].reason_code, "scraped")

    def test_infer_pattern_identifies_known_pattern(self) -> None:
        self.assertEqual(
            infer_pattern("Jane", "Doe", "jane.doe@example.com", "example.com"),
            "{first}.{last}",
        )
        self.assertEqual(
            infer_pattern("Jane", "Doe", "jdoe@example.com", "example.com"),
            "{f}{last}",
        )

    def test_update_pattern_stats_tracks_learning_state(self) -> None:
        domain_pattern = DomainPattern(domain="example.com", patterns=[])

        _update_pattern_stats(domain_pattern, "{f}{last}", success=False)
        _update_pattern_stats(domain_pattern, "{f}{last}", success=True)

        self.assertEqual(domain_pattern.last_successful_pattern, "{f}{last}")
        self.assertEqual(domain_pattern.patterns[0]["pattern"], "{f}{last}")
        self.assertEqual(domain_pattern.patterns[0]["total_count"], 2)
        self.assertEqual(domain_pattern.patterns[0]["success_count"], 1)
        self.assertGreater(domain_pattern.patterns[0]["confidence"], 0.0)


if __name__ == "__main__":
    unittest.main()
