from llm import client
from models import (
    ExperimentResult,
    ExperimentAnalysis,
    BusinessThreshold,
    EvidenceEvaluation
)
from research import evaluate_evidence
from decision import update_assumption_evidence, evaluate_assumption
from statistical_testing import (
    run_one_proportion_test,
    evaluate_business_significance,
    validate_threshold_for_testing
)
from threshold_validation import evaluate_threshold
from experiment_validation import (
    validate_experiment_result,
    validate_experiment_consistency
)
import json

def analyze_experiment_result(experiment_result):

    prompt = f"""
You are the experiment analysis component of LaunchProof AI.

Analyze the result of a real-world business experiment.

EXPERIMENT:
{experiment_result.experiment}

RESULT:
{experiment_result.result}

OBSERVATIONS:
{experiment_result.observations}

Your job is NOT to make the final business decision.

Determine what the experiment result tells us about the
original assumption.

Rules:

Rules:

1. Base the analysis only on the experiment result and observations.
2. Do not invent facts.
3. "Supports" means the experiment provides evidence in favor of the assumption.
4. "Contradicts" means the experiment provides evidence against the assumption.
5. "Unclear" means the evidence is insufficient or mixed.
6. support MUST be exactly one of:
   "Supports", "Contradicts", or "Unclear".
7. Never use "Mixed".
8. Return ONLY valid JSON.
Return exactly:

{{
    "support": "Supports",
    "strength": "Moderate",
    "evidence": "...",
    "explanation": "..."
}}
"""

    response = client.chat.completions.create(
        model="auto",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    result = response.choices[0].message.content

    print("\nExperiment Analysis:")
    print(result)

    if result.startswith("```"):
        result = result.strip()
        result = result.removeprefix("```json")
        result = result.removeprefix("```")
        result = result.removesuffix("```")
        result = result.strip()


    return ExperimentAnalysis.model_validate_json(result)


def apply_experiment_result(
    assumption,
    experiment,
    experiment_result,
    business_threshold
):
    # 0. Validate experiment data
    validate_experiment_result(experiment_result)
    
    consistency_warnings = validate_experiment_consistency(
        experiment,
        experiment_result
    )

    if consistency_warnings:
        print("\nExperiment Consistency Warnings:")

        for warning in consistency_warnings:
            print("-", warning)
    
    # 1. Validate the business threshold
    threshold_evaluation = evaluate_threshold(
        business_threshold
    )

    print("\nThreshold Evaluation:")
    print(threshold_evaluation)

    validate_threshold_for_testing(
        threshold_evaluation
    )

    # 2. Statistical analysis
    statistical_result = None
    business_significance = None

    if (
        experiment_result.sample_size is not None
        and experiment_result.successes is not None
    ):

        statistical_result = run_one_proportion_test(
            sample_size=experiment_result.sample_size,
            successes=experiment_result.successes,
            business_threshold=business_threshold,
            confidence_level=0.95
        )

        print("\nStatistical Result:")
        print(statistical_result)

        # 3. Business significance
        business_significance = evaluate_business_significance(
            statistical_result
        )

        print("\nBusiness Significance:")
        print(business_significance)

    # 4. Existing LLM experiment analysis
    analysis = analyze_experiment_result(
        experiment_result
    )

    print("\nExperiment Evidence:")
    print(analysis)

    # 5. Existing evidence evaluation
    experiment_evidence = f"""
    Experiment:
    {experiment_result.experiment}

    Result:
    {experiment_result.result}

    Observed conversion rate:
    {experiment_result.successes / experiment_result.sample_size:.1%}

    Business threshold:
    {business_threshold.value:.1%}

    Statistical classification:
    {business_significance.classification if business_significance else "Not available"}

    Experiment evidence:
    {analysis.evidence}
    """

    if business_significance:
        if business_significance.classification == "Above Threshold":
            support = "Supports"
        elif business_significance.classification == "Below Threshold":
            support = "Contradicts"
        else:
            support = "Unclear"

        evidence_evaluation = EvidenceEvaluation(
            relevance="High",
            support=support,
            strength=analysis.strength,
            explanation=business_significance.explanation
        )
    else:
        evidence_evaluation = EvidenceEvaluation(
            relevance="High",
            support=analysis.support,
            strength=analysis.strength,
            explanation=analysis.explanation
        )
    # 6. Update assumption
    updated_assumption = update_assumption_evidence(
        assumption=assumption,
        evidence=experiment_evidence,
        evidence_evaluation=evidence_evaluation
    )

    # 7. Existing decision logic
    updated_decision = evaluate_assumption(
        updated_assumption
    )

    return {
        "assumption": updated_assumption,
        "decision": updated_decision,
        "statistical_result": statistical_result,
        "business_significance": business_significance
    }