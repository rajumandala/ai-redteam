"""R4/R6: free measurement exercises. Standard library only; no target/model calls."""

import math
import unittest


def wilson(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Two-sided Wilson interval; assumes independent Bernoulli trials, not adaptive search."""
    if trials <= 0 or not 0 <= successes <= trials or not math.isfinite(z) or z <= 0:
        raise ValueError("need 0 <= successes <= trials, trials > 0, and finite z > 0")
    p = successes / trials
    denominator = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denominator
    margin = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denominator
    return max(0.0, centre - margin), min(1.0, centre + margin)


def zero_upper(trials: int, alpha: float = 0.05) -> float:
    """Exact one-sided upper bound when no independent trial succeeds."""
    if trials <= 0 or not 0 < alpha < 1:
        raise ValueError("need trials > 0 and 0 < alpha < 1")
    return -math.expm1(math.log(alpha) / trials)


def summarise(rows: list[dict]) -> dict:
    """Each row is one attempt: success/utility booleans, or an error (not both)."""
    completed = []
    for row in rows:
        if row.get("error"):
            if "success" in row or "utility" in row:
                raise ValueError("an error has no scored outcome")
        elif type(row.get("success")) is bool and type(row.get("utility")) is bool:
            completed.append(row)
        else:
            raise ValueError("completed attempts need boolean state grades")
    return {"attempted": len(rows), "completed": len(completed), "errors": len(rows) - len(completed),
            "successes": sum(r["success"] for r in completed),
            "utility": sum(r["utility"] for r in completed)}


class MeasurementChecks(unittest.TestCase):
    def test_zero_bound(self):
        self.assertAlmostEqual(zero_upper(10), 0.2588655509)

    def test_wilson_zero(self):
        low, high = wilson(0, 10)
        self.assertAlmostEqual(low, 0)
        self.assertAlmostEqual(high, 0.2775327999)

    def test_wilson_all(self):
        low, high = wilson(10, 10)
        self.assertAlmostEqual(low, 0.7224672001)
        self.assertAlmostEqual(high, 1)

    def test_interval_symmetry(self):
        low, high = wilson(3, 10)
        other_low, other_high = wilson(7, 10)
        self.assertAlmostEqual(low, 1 - other_high)
        self.assertAlmostEqual(high, 1 - other_low)

    def test_more_trials_tighter(self):
        self.assertLess(zero_upper(100), zero_upper(10))

    def test_invalid_counts(self):
        for successes, trials in [(0, 0), (-1, 10), (11, 10)]:
            with self.assertRaises(ValueError):
                wilson(successes, trials)
        with self.assertRaises(ValueError):
            zero_upper(0)

    def test_errors_separate(self):
        rows = [{"success": False, "utility": True}, {"error": "timeout"},
                {"success": True, "utility": False}]
        self.assertEqual(summarise(rows), {"attempted": 3, "completed": 2, "errors": 1, "successes": 1, "utility": 1})

    def test_unscored_rejected(self):
        for row in [{}, {"success": "yes", "utility": False}, {"error": "timeout", "success": False}]:
            with self.assertRaises(ValueError):
                summarise([row])

    def test_empty_not_zero_rate(self):
        summary = summarise([])
        self.assertEqual(summary["completed"], 0)
        with self.assertRaises(ValueError):
            wilson(summary["successes"], summary["completed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
