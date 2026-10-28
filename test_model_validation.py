
import unittest
from pydantic import ValidationError

from models import (
    BusinessProfile,
    Assumption,
    Experiment,
    ExperimentResult,
    EconomicThresholdBasis,
    BusinessThreshold,
)


class TestModelInputValidation(unittest.TestCase):

    def valid_business(self):
        return {
            "name": "Test Cafe",
            "idea": "Synthetic cafe for testing",
            "target_customer": "Local customers",
            "location": "Test location",
            "price": 100,
            "variable_cost": 40,
            "revenue_model": "Direct sales",
            "initial_budget": 5000,
        }

    def test_valid_business_is_accepted(self):
        business = BusinessProfile(**self.valid_business())
        self.assertEqual(business.price, 100)

    def test_missing_business_name_is_rejected(self):
        data = self.valid_business()
        del data["name"]

        with self.assertRaises(ValidationError):
            BusinessProfile(**data)

    def test_negative_business_price_is_rejected(self):
        data = self.valid_business()
        data["price"] = -10

        with self.assertRaises(ValidationError):
            BusinessProfile(**data)

    def test_negative_variable_cost_is_rejected(self):
        data = self.valid_business()
        data["variable_cost"] = -10

        with self.assertRaises(ValidationError):
            BusinessProfile(**data)

    def test_negative_initial_budget_is_rejected(self):
        data = self.valid_business()
        data["initial_budget"] = -100

        with self.assertRaises(ValidationError):
            BusinessProfile(**data)

    def test_invalid_assumption_importance_is_rejected(self):
        with self.assertRaises(ValidationError):
            Assumption(
                statement="Customers will pay",
                importance="Urgent",
                evidence="Synthetic evidence",
            )

    def test_negative_experiment_cost_is_rejected(self):
        with self.assertRaises(ValidationError):
            Experiment(
                assumption="Customers will pay",
                experiment="Synthetic survey",
                success_metric="5 positive responses",
                estimated_cost=-100,
                duration="1 day",
                planned_sample_size=10,
            )

    def test_zero_experiment_sample_size_is_rejected(self):
        with self.assertRaises(ValidationError):
            Experiment(
                assumption="Customers will pay",
                experiment="Synthetic survey",
                success_metric="5 positive responses",
                estimated_cost=100,
                duration="1 day",
                planned_sample_size=0,
            )

    def test_zero_economic_contribution_is_rejected(self):
        with self.assertRaises(ValidationError):
            EconomicThresholdBasis(
                required_contribution=0,
                contribution_per_unit=10,
                reachable_customers=100,
            )

    def test_threshold_above_one_is_rejected(self):
        with self.assertRaises(ValidationError):
            BusinessThreshold(
                metric="Conversion rate",
                value=1.2,
                source="user_defined",
                rationale="Synthetic test",
            )

    def test_successes_cannot_exceed_sample_size(self):
        with self.assertRaises(ValidationError):
            ExperimentResult(
                experiment="Synthetic survey",
                sample_size=10,
                successes=12,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
