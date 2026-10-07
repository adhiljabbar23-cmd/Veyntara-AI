from models import BusinessThreshold, ThresholdEvaluation


def evaluate_threshold(threshold: BusinessThreshold):

    if threshold.source == "derived_from_economics":

        if threshold.economic_basis is None:
            return ThresholdEvaluation(
                strength="Weak",
                valid=False,
                explanation=(
                    "The threshold is marked as economically derived, "
                    "but no economic basis was provided."
                )
            )

        validation = validate_economic_threshold(threshold)

        if not validation["valid"]:
            return ThresholdEvaluation(
                strength="Weak",
                valid=False,
                explanation=validation["message"]
            )

        return ThresholdEvaluation(
            strength="Strong",
            valid=True,
            explanation=(
                "The threshold matches the independently calculated "
                "economic requirement."
            )
        )

    elif threshold.source == "external_requirement":

        if len(threshold.rationale.strip()) < 20:
            return ThresholdEvaluation(
                strength="Weak",
                valid=True,
                explanation=(
                    "An external requirement is claimed, but the "
                    "rationale does not provide enough information."
                )
            )

        return ThresholdEvaluation(
            strength="Strong",
            valid=True,
            explanation=(
                "The threshold is based on an external requirement "
                "with a documented rationale."
            )
        )

    elif threshold.source == "user_defined":

        if len(threshold.rationale.strip()) < 20:
            return ThresholdEvaluation(
                strength="Weak",
                valid=True,
                explanation=(
                    "The threshold is user-defined, but its rationale "
                    "is too limited to establish why it is appropriate."
                )
            )

        return ThresholdEvaluation(
            strength="Moderate",
            valid=True,
            explanation=(
                "The threshold is explicitly defined by the user "
                "with a documented business rationale."
            )
        )
        
def calculate_economic_threshold(threshold):

    if threshold.economic_basis is None:
        raise ValueError(
            "Economic basis is required when calculating "
            "an economically derived threshold."
        )

    basis = threshold.economic_basis

    required_units = (
        basis.required_contribution
        / basis.contribution_per_unit
    )

    required_rate = (
        required_units
        / basis.reachable_customers
    )

    return required_rate

def validate_economic_threshold(threshold):

    calculated_rate = calculate_economic_threshold(threshold)

    difference = abs(
        calculated_rate - threshold.value
    )

    if difference < 0.000001:
        return {
            "valid": True,
            "calculated_rate": calculated_rate,
            "provided_rate": threshold.value,
            "message": "The provided threshold matches the economic calculation."
        }

    return {
        "valid": False,
        "calculated_rate": calculated_rate,
        "provided_rate": threshold.value,
        "message": "The provided threshold does not match the economic calculation."
    }