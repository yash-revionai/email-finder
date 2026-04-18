import unittest

from app.services.pattern_engine import PATTERNS, generate_candidates, global_weight


class GlobalWeightTests(unittest.TestCase):
    def test_global_weight_matches_expected_bounds(self) -> None:
        self.assertEqual(global_weight(0), 0.7)
        self.assertEqual(global_weight(len(PATTERNS) - 1), 0.3)

    def test_generate_candidates_uses_global_order_without_history(self) -> None:
        candidates = generate_candidates("John", "Doe", "Example.com", None)

        self.assertEqual(len(candidates), len(PATTERNS))
        self.assertEqual(candidates[0], ("john.doe@example.com", global_weight(0)))
        self.assertEqual(candidates[-1], ("doe_john@example.com", global_weight(len(PATTERNS) - 1)))

    def test_generate_candidates_uses_stored_pattern_confidence(self) -> None:
        history = {
            "patterns": [
                {
                    "pattern": "{f}{last}",
                    "confidence": 0.95,
                    "success_count": 12,
                    "total_count": 14,
                }
            ]
        }

        candidates = generate_candidates("John", "Doe", "example.com", history)

        self.assertEqual(candidates[0], ("jdoe@example.com", 0.95))

    def test_generate_candidates_deduplicates_emails(self) -> None:
        candidates = generate_candidates("J", "J", "example.com", None)
        unique_emails = {email for email, _ in candidates}

        self.assertEqual(len(unique_emails), len(candidates))


if __name__ == "__main__":
    unittest.main()
