from scipy.stats import binomtest
from statsmodels.stats.proportion import proportion_confint
from models import (
    BusinessThreshold,
    StatisticalResult,
    BusinessSignificance
)

from models import StatisticalResult


def run_one_proportion_test(
    sample_size,
    successes,
    business_threshold,
    confidence_level=0.95
):
    
    threshold = business_threshold.value
    observed_rate = successes / sample_size

    significance_level = 1 - confidence_level

    # Wilson confidence interval
    confidence_interval = proportion_confint(
        count=successes,
        nobs=sample_size,
        alpha=significance_level,
        method="wilson"
    )

    # Exact one-sided binomial test
    test = binomtest(
        k=successes,
        n=sample_size,
        p=threshold,
        alternative="greater"
    )

    p_value = test.pvalue

    statistically_significant = (
        p_value < significance_level
    )

    return StatisticalResult(
        sample_size=sample_size,
        successes=successes,
        observed_rate=observed_rate,
        threshold=threshold,
        confidence_interval=confidence_interval,
        confidence_level=confidence_level,
        p_value=p_value,
        significance_level=significance_level,
        statistically_significant=statistically_significant
    )
    
def evaluate_business_significance(
    statistical_result: StatisticalResult
):

    lower_bound, upper_bound = statistical_result.confidence_interval
    threshold = statistical_result.threshold

    if lower_bound > threshold:

        classification = "Above Threshold"

        explanation = (
            f"The entire confidence interval is above the "
            f"business threshold of {threshold:.1%}. "
            f"The observed rate is {statistical_result.observed_rate:.1%}, "
            f"and the confidence interval ranges from "
            f"{lower_bound:.1%} to {upper_bound:.1%}."
        )

    elif upper_bound < threshold:

        classification = "Below Threshold"

        explanation = (
            f"The entire confidence interval is below the "
            f"business threshold of {threshold:.1%}. "
            f"The observed rate is {statistical_result.observed_rate:.1%}, "
            f"and the confidence interval ranges from "
            f"{lower_bound:.1%} to {upper_bound:.1%}."
        )

    else:

        classification = "Uncertain"

        explanation = (
            f"The confidence interval crosses the business "
            f"threshold of {threshold:.1%}. "
            f"The observed rate is {statistical_result.observed_rate:.1%}, "
            f"but the confidence interval ranges from "
            f"{lower_bound:.1%} to {upper_bound:.1%}."
        )

    return BusinessSignificance(
        required_rate=threshold,
        observed_rate=statistical_result.observed_rate,
        confidence_interval=statistical_result.confidence_interval,
        classification=classification,
        explanation=explanation
    )
    
def validate_threshold_for_testing(threshold_evaluation):

    if not threshold_evaluation.valid:
        raise ValueError(
            "Statistical business-significance testing cannot proceed "
            "because the business threshold is invalid."
        )

    return True