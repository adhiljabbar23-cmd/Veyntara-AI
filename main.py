from models import (
    BusinessProfile,
    AssumptionList,
    ExperimentResult,
    BusinessThreshold,
    EconomicThresholdBasis,
    EvidenceEvaluation
)

import json
from modifications import generate_modification

from agent import ask_ai
from decision import evaluate_all_assumptions, make_decision
from experiments import generate_experiment
from experiment_results import apply_experiment_result
from research import evaluate_evidence
from database import (
    initialize_database,
    save_business,
    get_business,
    get_all_businesses,
    save_assumption,
    update_assumption_evaluation,
    get_assumptions,
    save_experiment,
    get_experiments
)

initialize_database()

print("\n1. Create a new business")
print("2. Continue an existing business")

choice = input("\nChoose an option: ")

if choice == "2":
    businesses = get_all_businesses()

    if not businesses:
        print("\nNo existing businesses found.")
        exit()

    print("\nExisting businesses:")

    for business in businesses:
        print(
            f"ID: {business[0]} | "
            f"Name: {business[1]} | "
            f"Idea: {business[2]}"
        )

    business_id = int(input("\nEnter business ID: "))

    existing_business = get_business(business_id)

    if existing_business is None:
        print("\nBusiness not found.")
        exit()

    business = BusinessProfile(
        name=existing_business[1],
        idea=existing_business[2],
        target_customer=existing_business[3],
        location=existing_business[4],
        price=existing_business[5],
        revenue_model=existing_business[6],
        initial_budget=existing_business[7]
    )
    business_id = existing_business[0]
    print(f"\nContinuing business: {business.name}")
    existing_assumptions = get_assumptions(business_id)

    print("\nExisting assumptions:")

    for assumption in existing_assumptions:
        print(
            f"ID: {assumption[0]} | "
            f"Importance: {assumption[2]} | "
            f"Risk: {assumption[4]} | "
            f"Confidence: {assumption[5]}"
        )
        # Find assumptions that still need validation
    unvalidated_assumptions = [
        assumption
        for assumption in existing_assumptions
        if assumption[4] is None or assumption[5] is None
    ]

    if not unvalidated_assumptions:
        print("\nAll assumptions have been validated.")
        exit()

    # Prioritize High importance assumptions first
    unvalidated_assumptions.sort(
        key=lambda x: 0 if x[2] == "High" else 1
    )

    next_assumption = unvalidated_assumptions[0]

    print("\nNext assumption to validate:")
    print(f"ID: {next_assumption[0]}")
    print(f"Statement: {next_assumption[1]}")
    print(f"Importance: {next_assumption[2]}")  
    
    previous_experiments = get_experiments(business_id)

    print("\nPrevious experiments:")

    if not previous_experiments:
        print("No previous experiments found.")
    else:
        for experiment in previous_experiments:
            print(
                f"ID: {experiment[0]} | "
                f"Assumption ID: {experiment[1]} | "
                f"Experiment: {experiment[2]}"
            )
        # Check whether the selected assumption has already been tested
    assumption_experiments = [
        experiment
        for experiment in previous_experiments
        if experiment[1] == next_assumption[0]
    ]

    if assumption_experiments:
        print(
            f"\nPrevious experiments found for assumption "
            f"{next_assumption[0]}:"
        )

        for experiment in assumption_experiments:
            print(
                f"Experiment ID: {experiment[0]}"
            )
            print(
                f"Experiment: {experiment[2]}"
            )
            print(
                f"Result: {experiment[3]}"
            )
            print(
                f"Observations: {experiment[4]}"
            )
    else:
        print(
            f"\nNo previous experiment found for assumption "
            f"{next_assumption[0]}."
        )

        # Generate an experiment for the selected assumption
        print("\nGenerating validation experiment...")

        experiment = generate_experiment(
            assumption=next_assumption[1]
        )

        print("\nExperiment for selected assumption:")
        print(f"Experiment: {experiment.experiment}")
        print(f"Success metric: {experiment.success_metric}")
        print(f"Estimated cost: {experiment.estimated_cost}")
        print(f"Duration: {experiment.duration}")
        print(f"Planned sample size: {experiment.planned_sample_size}")
    
                # Save the experiment to the database
        experiment_id = save_experiment(
            business_id=business_id,
            assumption_id=next_assumption[0],
            experiment=experiment,
            experiment_result=ExperimentResult(
                experiment=experiment.experiment,
                result=None,
                observations=None,
                sample_size=None,
                successes=None
            )
        )

        print(f"\nExperiment saved with ID: {experiment_id}")
    
else:
    business = BusinessProfile(
        name="FreshBite",
        idea="Healthy meal delivery for college students",
        target_customer="college students",
        location="Kochi",
        price=120,
        revenue_model="per-meal purchase",
        initial_budget=50000
    )

    business_id = save_business(business)
    print(f"\nBusiness saved with ID: {business_id}")
    




    question = f"""
    You are LaunchProof AI, a business validation agent.

    Your job is NOT to create a business plan.

    Your job is to identify the assumptions that must be true
    for the business to succeed.

    Business information:

    Business name: {business.name}
    Business idea: {business.idea}
    Target customer: {business.target_customer}
    Location: {business.location}
    Price per unit: ₹{business.price}
    Revenue model: {business.revenue_model}
    Initial budget: ₹{business.initial_budget}

    Identify the 5 most important assumptions behind this
    business idea.

    For each assumption provide:

    - statement
    - importance
    - evidence


    Rules:

    1. Do NOT invent evidence.

    2. If evidence is unavailable, say:
    "Evidence not yet available."

    3. Use the search_web tool when external information
    could help investigate an assumption.


    4. Do not automatically treat search results as valid
    evidence.

    5. If evidence is indirect or does not directly answer
    the assumption, treat it as "Unclear".



    6. Do not search for every possible piece of information.
    Prioritize the most important assumptions.

    7. If useful evidence cannot be found, stop searching
    and mark the evidence as:
    "Evidence not yet available."

    8. Do not treat a competitor's selling price as evidence
        of their production cost.

    9. Importance must be exactly one of:
        "Low", "Medium", "High".



    10. You do not need to investigate every assumption.
        If evidence is unavailable after a reasonable search,
        mark it as "Evidence not yet available" and move on.

    11. Once you have enough information to produce the
        5 assumptions, immediately return the final JSON.

    12. Never continue searching indefinitely.

    13. Return ONLY valid JSON.

    The JSON must follow this exact structure:

    {{
        "assumptions": [
            {{
                "statement": "...",
                "importance": "High",
                "evidence": "..."
            }}
        ]
    }}


    """
    answer = ask_ai(question)

    if answer.startswith("```"):
        answer = answer.strip()
        answer = answer.removeprefix("```json")
        answer = answer.removeprefix("```")
        answer = answer.removesuffix("```")
        answer = answer.strip()

    raw_assumptions = AssumptionList.model_validate_json(answer)

    print("\nRaw AI Response")
    print(answer)

    if answer == "The agent reached its research limit.":
        print("\nThe agent did not finish within the research limit.")
        
    else:    
        raw_assumptions = AssumptionList.model_validate_json(answer)

        evaluation_input = []

        for assumption in raw_assumptions.assumptions:
            evaluation_input.append({
                "statement": assumption.statement,
                "evidence": assumption.evidence
            })

        evaluation_result = evaluate_evidence(evaluation_input)

        evaluation_data = json.loads(evaluation_result)

        evaluations = evaluation_data["evaluations"]

        if len(evaluations) != len(raw_assumptions.assumptions):
            raise ValueError(
                "Number of evaluations does not match number of assumptions."
            )

        for assumption, evaluation in zip(
            raw_assumptions.assumptions,
            evaluations
        ):
            assumption.evaluation = EvidenceEvaluation.model_validate(evaluation)

        assumptions = raw_assumptions

        print("\nValidated Response")
        print(assumptions)


        decision_results = evaluate_all_assumptions(
            assumptions.assumptions
        )
        assumption_ids = []

        for assumption in assumptions.assumptions:
            assumption_id = save_assumption(
                business_id=business_id,
                assumption=assumption
            )
            assumption_ids.append(assumption_id)

        saved_assumptions = get_assumptions(business_id)

        print("\nSaved assumptions in database:")

        for assumption in saved_assumptions:
            print(assumption)
        print("Decison Anlysis")
        
        for result in decision_results:
            print(result)
            
        decision = make_decision(decision_results)

        print("\nOverall Decision")
        print(decision["decision"])

        print("\nWhy?")
        print(decision["reason"])

        print("\nOverall Risk")
        print(decision["overall_risk"])

        print("\nEvidence Gaps")

        for gap in decision["evidence_gaps"]:

            print("\n-", gap["statement"])
            print("  Reason:", gap["reason"])
            
        print("\nPriority Assumptions")

        for item in decision["priority_assumptions"]:

            print("\n-", item["statement"])
            print("  Importance:", item["importance"])
            print("  Risk:", item["risk"])
            print("  Confidence:", item["confidence"])
            print("  Priority Score:", item["priority_score"])
            
        if decision["priority_assumptions"]:

            top_assumption = decision["priority_assumptions"][0]

            print("\nRecommended Experiment")

            experiment = generate_experiment(
                top_assumption["statement"]
            )

            print("\nAssumption:")
            print(experiment.assumption)

            print("\nExperiment:")
            print(experiment.experiment)

            print("\nSuccess Metric:")
            print(experiment.success_metric)

            print("\nEstimated Cost:")
            print(experiment.estimated_cost)

            print("\nDuration:")
            print(experiment.duration)
                    
            print("\n--- Experiment Feedback ---")

            result_text = input("What happened in the experiment? ")

            observations = input("What did you observe? ")

            sample_size_input = input(
                "How many people participated? (press Enter if not applicable): "
            )

            successes_input = input(
                "How many successful outcomes? (press Enter if not applicable): "
            )

            sample_size = (
                int(sample_size_input)
                if sample_size_input.strip()
                else None
            )

            successes = (
                int(successes_input)
                if successes_input.strip()
                else None
            )

            experiment_result = ExperimentResult(
                experiment=experiment.experiment,
                result=result_text,
                observations=observations,
                sample_size=sample_size,
                successes=successes
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
            updated = apply_experiment_result(
                assumption=assumptions.assumptions[0],
                experiment=experiment,
                experiment_result=experiment_result,
                business_threshold=threshold
            )
            experiment_id = save_experiment(
                business_id=business_id,
                assumption_id=assumption_ids[0],
                experiment=experiment,
                experiment_result=experiment_result
            )
            
            saved_experiments = get_experiments(business_id)



            print("\nSaved experiments in database:")

            for experiment in saved_experiments:
                print(experiment)

            print(f"\nExperiment saved with ID: {experiment_id}")

            print("\nUpdated Assumption:")
            print(updated["assumption"])

            print("\nUpdated Decision Analysis:")
            print(updated["decision"])

            # Replace the old assumption with the experiment-updated assumption
            updated_assumptions = assumptions.assumptions.copy()

            updated_assumptions[0] = updated["assumption"]

            # Re-evaluate all assumptions
            final_results = evaluate_all_assumptions(
                updated_assumptions
            )

            # Make the final business decision
            final_decision = make_decision(final_results)

            print("\n==============================")
            print("FINAL BUSINESS DECISION")
            print("==============================")

            print("\nDecision:")
            print(final_decision["decision"])

            print("\nWhy?")
            print(final_decision["reason"])

            print("\nOverall Risk:")
            print(final_decision["overall_risk"])
            
            print("\nUnvalidated Assumptions")
            print(final_decision["uncertainty_count"])

            if final_decision["decision"] == "Launch":
                print("\nRecommendation:")
                print("The business is ready to proceed based on the validated assumptions.")

            elif final_decision["decision"] == "Modify":
                print("\nRecommendation:")
                print("Modify the affected part of the business and run another experiment.")

            elif final_decision["decision"] == "Test More":
                print("\nRecommendation:")
                print("More evidence is required before making a launch decision.")

            elif final_decision["decision"] == "Don't Launch":
                print("\nRecommendation:")
                print("Do not launch the current business model because a critical assumption has strong contradictory evidence.")

            if final_decision["decision"] == "Modify":
                modification = generate_modification(
                    assumption=updated["assumption"],
                    experiment_result=experiment_result,
                    decision=final_decision["decision"]
                )

                print("\n==============================")
                print("MODIFICATION RECOMMENDATION")
                print("==============================")

                print("\nProblem:")
                print(modification.problem)

                print("\nEvidence:")
                print(modification.evidence)

                print("\nModification:")
                print(modification.modification)

                print("\nReason:")
                print(modification.reason)

                print("\nNext Experiment:")
                print(modification.next_experiment)


