import unittest

from calculations import (
    calculate_financials,
    calculate_required_units,
)


class TestCalculationInputValidation(unittest.TestCase):

    def test_zero_selling_price_is_rejected(self):
        result = calculate_financials(0, 0, 100)
        self.assertIn("error", result)

    def test_negative_variable_cost_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_financials(100, -10, 500)

    def test_negative_fixed_cost_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_financials(100, 40, -500)

    def test_negative_required_contribution_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_required_units(-100, 100, 40)

    def test_missing_price_is_handled(self):
        with self.assertRaises((TypeError, ValueError)):
            calculate_financials(None, 40, 500)

    def test_text_price_is_handled(self):
        with self.assertRaises((TypeError, ValueError)):
            calculate_financials("abc", 40, 500)


if __name__ == "__main__":
    unittest.main(verbosity=2)
