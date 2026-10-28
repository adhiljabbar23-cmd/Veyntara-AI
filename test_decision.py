import unittest

from decision import (
    make_decision,
    calculate_overall_risk,
    calculate_uncertainty,
    find_critical_risks,
    find_unknowns,
    find_priority_assumptions,
)


def synthetic_result(
    importance="High",
    risk="Low Risk",
    confidence="High",
    strength="Strong",
    statement="Synthetic test assumption",
):
    return {
        "statement": statement,
        "importance": importance,
        "risk": risk,
        "confidence": confidence,
        "strength": strength,
        "explanation": "Synthetic evidence for testing only",
    }


class TestDecisionLogic(unittest.TestCase):

    def test_launch_when_important_assumptions_are_supported(self):
        results = [synthetic_result()]

        self.assertEqual(make_decision(results)["decision"], "Launch")

    def test_dont_launch_for_strong_critical_contradiction(self):
        results = [
            synthetic_result(
                risk="High Risk",
                strength="Strong",
            )
        ]

        self.assertEqual(
            make_decision(results)["decision"],
            "Don't Launch",
        )

    def test_modify_for_moderate_critical_contradiction(self):
        results = [
            synthetic_result(
                risk="High Risk",
                strength="Moderate",
            )
        ]

        self.assertEqual(make_decision(results)["decision"], "Modify")

    def test_test_more_when_critical_assumption_is_unknown(self):
        results = [
            synthetic_result(
                risk="Unknown",
                confidence="Low",
            )
        ]

        self.assertEqual(make_decision(results)["decision"], "Test More")

    def test_uncertainty_counts_unknown_assumptions(self):
        results = [
            synthetic_result(risk="Unknown"),
            synthetic_result(risk="Low Risk"),
            synthetic_result(risk="Unknown"),
        ]

        self.assertEqual(calculate_uncertainty(results), 2)

    def test_unknown_risks_are_excluded_from_overall_risk(self):
        results = [
            synthetic_result(
                importance="High",
                risk="High Risk",
            ),
            synthetic_result(
                importance="High",
                risk="Unknown",
            ),
        ]

        self.assertEqual(calculate_overall_risk(results), 2.0)

    def test_overall_risk_is_zero_when_all_risks_are_unknown(self):
        results = [
            synthetic_result(risk="Unknown"),
        ]

        self.assertEqual(calculate_overall_risk(results), 0)

    def test_critical_risks_include_only_high_importance_high_risk(self):
        critical = synthetic_result(
            importance="High",
            risk="High Risk",
        )
        medium_importance = synthetic_result(
            importance="Medium",
            risk="High Risk",
        )
        low_risk = synthetic_result(
            importance="High",
            risk="Low Risk",
        )

        found = find_critical_risks(
            [critical, medium_importance, low_risk]
        )

        self.assertEqual(found, [critical])

    def test_unknowns_include_only_high_importance_unknowns(self):
        critical_unknown = synthetic_result(
            importance="High",
            risk="Unknown",
        )
        medium_unknown = synthetic_result(
            importance="Medium",
            risk="Unknown",
        )

        found = find_unknowns([critical_unknown, medium_unknown])

        self.assertEqual(found, [critical_unknown])

    def test_priority_assumptions_are_sorted_highest_first(self):
        low_priority = synthetic_result(
            importance="Low",
            risk="Low Risk",
            confidence="High",
            statement="Low priority synthetic assumption",
        )
        high_priority = synthetic_result(
            importance="High",
            risk="High Risk",
            confidence="Low",
            statement="High priority synthetic assumption",
        )

        ranked = find_priority_assumptions(
            [low_priority, high_priority]
        )

        self.assertEqual(
            ranked[0]["statement"],
            "High priority synthetic assumption",
        )
        self.assertGreater(
            ranked[0]["priority_score"],
            ranked[1]["priority_score"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
