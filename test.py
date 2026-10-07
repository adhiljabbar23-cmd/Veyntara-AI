from models import (
    BusinessThreshold,
    EconomicThresholdBasis
)

from threshold_validation import evaluate_threshold

from statistical_testing import (
    run_one_proportion_test,
    evaluate_business_significance,
    validate_threshold_for_testing
)


threshold = BusinessThreshold(
    metric="purchase_rate",
    value=0.20,
    source="derived_from_economics",
    rationale=(
        "The threshold is derived from the required "
        "contribution and expected reachable customers."
    ),
    economic_basis=EconomicThresholdBasis(
        required_contribution=40000,
        contribution_per_unit=40,
        reachable_customers=5000
    )
)

threshold_evaluation = evaluate_threshold(threshold)

validate_threshold_for_testing(threshold_evaluation)

statistical_result = run_one_proportion_test(
    sample_size=50,
    successes=12,
    business_threshold=threshold,
    confidence_level=0.95
)

business_result = evaluate_business_significance(
    statistical_result
)

print("\nBUSINESS SIGNIFICANCE")
print(business_result)