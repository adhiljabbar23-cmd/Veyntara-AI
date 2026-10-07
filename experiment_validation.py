def validate_experiment_result(experiment_result):

    if (
        experiment_result.sample_size is not None
        and experiment_result.sample_size <= 0
    ):
        raise ValueError(
            "Sample size must be greater than 0."
        )

    if (
        experiment_result.successes is not None
        and experiment_result.successes < 0
    ):
        raise ValueError(
            "Number of successes cannot be negative."
        )

    if (
        experiment_result.sample_size is not None
        and experiment_result.successes is not None
        and experiment_result.successes > experiment_result.sample_size
    ):
        raise ValueError(
            "Number of successes cannot exceed sample size."
        )

    return True


def validate_experiment_consistency(
    experiment,
    experiment_result
):

    warnings = []

    planned_sample_size = experiment.planned_sample_size
    actual_sample_size = experiment_result.sample_size

    if (
        planned_sample_size is not None
        and actual_sample_size is not None
        and planned_sample_size != actual_sample_size
    ):

        warnings.append(
            f"The experiment planned for "
            f"{planned_sample_size} participants, "
            f"but the feedback reports "
            f"{actual_sample_size} participants."
        )

    return warnings