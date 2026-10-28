import unittest

from calculations import (
    calculate_required_units,
    calculate_financials,
)


class TestCalculations(unittest.TestCase):

    def test_required_units_rounds_up(self):
        result = calculate_required_units(
            required_contribution=1000,
            price=100,
            variable_cost=60,
        )

        self.assertEqual(result["contribution_per_unit"], 40)
        self.assertEqual(result["required_units"], 25)

    def test_required_units_rounds_fraction_up(self):
        result = calculate_required_units(
            required_contribution=1001,
            price=100,
            variable_cost=60,
        )

        self.assertEqual(result["required_units"], 26)

    def test_required_units_returns_none_when_no_contribution(self):
        result = calculate_required_units(
            required_contribution=1000,
            price=50,
            variable_cost=50,
        )

        self.assertIsNone(result)

    def test_required_units_returns_none_when_cost_exceeds_price(self):
        result = calculate_required_units(
            required_contribution=1000,
            price=40,
            variable_cost=50,
        )

        self.assertIsNone(result)

    def test_break_even_units(self):
        result = calculate_financials(
            price=100,
            variable_cost=60,
            fixed_cost=1000,
        )

        self.assertEqual(result["contribution_per_unit"], 40)
        self.assertEqual(result["break_even_units"], 25)

    def test_break_even_units_rounds_up(self):
        result = calculate_financials(
            price=100,
            variable_cost=60,
            fixed_cost=1001,
        )

        self.assertEqual(result["break_even_units"], 26)

    def test_financials_reject_price_equal_to_variable_cost(self):
        result = calculate_financials(
            price=50,
            variable_cost=50,
            fixed_cost=1000,
        )

        self.assertIn("error", result)

    def test_financials_reject_variable_cost_above_price(self):
        result = calculate_financials(
            price=40,
            variable_cost=50,
            fixed_cost=1000,
        )

        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
