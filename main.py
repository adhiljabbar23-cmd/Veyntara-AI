from models import (
    BusinessProfile,
    AssumptionList,
    ExperimentResult,
    BusinessThreshold,
    EconomicThresholdBasis,
    EvidenceEvaluation,
    Experiment,
    Assumption
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
    get_experiments,
    update_experiment_result
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

    try:
        business_id = int(input("\nEnter business ID: "))
    except ValueError:
        print("\nInvalid business ID. Please enter a number.")
        exit()

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
        variable_cost=existing_business[6],
        revenue_model=existing_business[7],
        initial_budget=existing_business[8]
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
    
        


    # Get all experiments before selecting an assumption
    previous_experiments = get_experiments(business_id)

    # Group experiments by assumption ID
    experiments_by_assumption = {}

    for experiment in previous_experiments:
        assumption_id = experiment[1]
        experiments_by_assumption.setdefault(assumption_id, []).append(experiment)

  
    # Find assumptions that still need validation
    planned_candidates = []
    unevaluated_candidates = []

    for assumption in existing_assumptions:
        assumption_id = assumption[0]
        assumption_experiments = experiments_by_assumption.get(
            assumption_id, []
        )

        # Resume an assumption that already has a planned experiment
        planned_experiments = [
            experiment
            for experiment in assumption_experiments
            if experiment[11] == "planned"
        ]

        if planned_experiments:
            planned_candidates.append(assumption)
            continue

        # Check whether the assumption still needs evaluation
        needs_evaluation = (
            assumption[4] is None
            or assumption[5] is None
            or assumption[5] == "Low"
        )

        if needs_evaluation:
            unevaluated_candidates.append(assumption)

    # Prefer resuming existing planned experiments
    if planned_candidates:
        candidates = planned_candidates
    else:
        candidates = unevaluated_candidates

    if not candidates:
        print("\nNo assumptions currently need validation.")
        exit()

    # Prioritize importance: High, Medium, Low
    importance_order = {
        "High": 0,
        "Medium": 1,
        "Low": 2
    }

    candidates.sort(
        key=lambda assumption: importance_order.get(
            assumption[2], 3
        )
    )

    next_assumption = candidates[0]

    print("\nNext assumption to validate:")
    print(f"ID: {next_assumption[0]}")
    print(f"Statement: {next_assumption[1]}")
    print(f"Importance: {next_assumption[2]}")

    

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
            print(f"Experiment ID: {experiment[0]}")
            print(f"Experiment: {experiment[2]}")
            print(f"Result: {experiment[7]}")
            print(f"Observations: {experiment[8]}")

    # Select an existing planned experiment, if one exists
    planned_experiments = [
        experiment
        for experiment in assumption_experiments
        if experiment[11] == "planned"
    ]

    if planned_experiments:
        latest_experiment = planned_experiments[-1]

    else:
        print("\nNo planned experiment found for this assumption.")
        print("Generating a new validation experiment...")

        experiment = generate_experiment(
            assumption=next_assumption[1]
        )

        experiment_id = save_experiment(
            business_id=business_id,
            assumption_id=next_assumption[0],
            experiment=experiment
        )

        # Reload experiments to obtain the saved record
        all_experiments = get_experiments(business_id)

        latest_experiment = next(
            item for item in all_experiments
            if item[0] == experiment_id
        )

    print("\nExperiment selected:")
    print(f"Experiment ID: {latest_experiment[0]}")
    print(f"Status: {latest_experiment[11]}")
    print(f"Experiment: {latest_experiment[2]}")

        

    if latest_experiment[11] == "planned":
        print("\nExperiment status: PLANNED")
        print("1. Enter experiment results")
        print("2. Exit and record results later")

        result_choice = input("Choose an option: ").strip()

        if result_choice != "1":
            print("\nExperiment remains saved as planned.")
            exit()

            
        result_text = input(
            "\nWhat happened in the experiment? "
        )

        observations = input(
            "What did you observe? "
        )

        sample_size_input = input(
            "How many people participated? "
            "(press Enter if not applicable): "
        )

        successes_input = input(
            "How many successful outcomes? "
            "(press Enter if not applicable): "
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
            experiment=latest_experiment[2],
            result=result_text,
            observations=observations,
            sample_size=sample_size,
            successes=successes
        )

        print("\nExperiment Result:")
        print(experiment_result)
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
        experiment_object = Experiment(
            assumption=next_assumption[1],
            experiment=latest_experiment[2],
            success_metric=latest_experiment[3],
            estimated_cost=latest_experiment[4],
            duration=latest_experiment[5],
            planned_sample_size=latest_experiment[6]
        )
        
        assumption_object = Assumption(
            statement=next_assumption[1],
            importance=next_assumption[2],
            evidence=next_assumption[3],
            evaluation=None
        )
        
        updated = apply_experiment_result(
            assumption=assumption_object,
            experiment=experiment_object,
            experiment_result=experiment_result,
            business_threshold=threshold
        )

        update_assumption_evaluation(
        assumption_id=next_assumption[0],
            risk=updated["decision"]["risk"],
            confidence=updated["decision"]["confidence"]
        )

        print("\nAssumption evaluation saved to database.")
        
        update_experiment_result(
                experiment_id=latest_experiment[0],
                experiment_result=experiment_result
            )

        print("\nExperiment result saved to database.")
                    
        
        saved_assumptions = get_assumptions(business_id)

        print("\nUpdated assumptions in database:")
        for assumption in saved_assumptions:
            print(assumption)
        print("\nExperiment Analysis:")
        print(updated)
        

    else:
        print("\nThis experiment has already been completed.")
        print("Its saved result is:")
        print(f"Result: {latest_experiment[7]}")
        print(f"Observations: {latest_experiment[8]}")
        print("No new experiment was created.")

    
elif choice == "1":
    business = BusinessProfile(
        name="SkillBridge",
        idea="Affordable weekend coding workshops",
        target_customer="College students and beginners",
        location="Kochi",
        price=499,
        variable_cost=150,
        revenue_model="Per-person workshop fee1",
        initial_budget=30000
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


    print("\nRaw AI Response")
    print(answer)

    if answer.strip() == "The agent reached its research limit.":
        print("\nThe agent did not finish within the research limit.")
        exit()

    # Extract the first valid JSON object
    decoder = json.JSONDecoder()
    json_start = answer.find("{")

    if json_start == -1:
        raise ValueError("AI response did not contain a JSON object.")

    parsed_json, _ = decoder.raw_decode(answer[json_start:])
    raw_assumptions = AssumptionList.model_validate(parsed_json)

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

    for assumption, decision in zip(
        assumptions.assumptions,
        decision_results
    ):
        assumption_id = save_assumption(
            business_id=business_id,
            assumption=assumption
        )

        update_assumption_evaluation(
            assumption_id=assumption_id,
            risk=decision["risk"],
            confidence=decision["confidence"]
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

            top_assumption_index = top_assumption["original_index"]

            top_assumption_object = assumptions.assumptions[
                top_assumption_index
            ]

            top_assumption_id = assumption_ids[top_assumption_index]
            
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
                    
            
            print("\n--- Experiment Status ---")
            conducted = input(
                "Have you actually conducted this experiment? (y/n): "
            ).strip().lower()

            if conducted != "y":
                # Save the experiment as planned, without fake results.
                experiment_id = save_experiment(
                    business_id=business_id,
                    assumption_id=top_assumption_id,
                    experiment=experiment,
                    experiment_result=None
                )

                print(f"\nExperiment saved with ID: {experiment_id}")
                print("Status: planned")
                print("No experiment results or evidence were recorded.")
                print("Run the experiment and record real results later.")

                exit()

            result_text = input("What actually happened? ").strip()
            observations = input("What did you observe? ").strip()

            sample_size_input = input(
                "How many people participated? (Enter if not applicable): "
            ).strip()

            successes_input = input(
                "How many successful outcomes? (Enter if not applicable): "
            ).strip()

            sample_size = (
                int(sample_size_input)
                if sample_size_input
                else None
            )

            successes = (
                int(successes_input)
                if successes_input
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
                assumption=top_assumption_object,
                experiment=experiment,
                experiment_result=experiment_result,
                business_threshold=threshold,
                business=business
            )



            experiment_id = save_experiment(
                business_id=business_id,
                assumption_id=top_assumption_id,
                experiment=experiment,
                experiment_result=experiment_result
            )

            update_experiment_result(
                experiment_id=experiment_id,
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

            updated_assumptions[top_assumption_index] = updated["assumption"]

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

else:
    print("\nInvalid choice. Please enter 1 or 2.")
    exit()

# Great! Let's take the next step in Veyntara AI.

# ## Step 4 — Improve experiment quality

# Your workflow now resumes planned experiments and avoids duplicate experiment-selection output. Next, we should ensure that each experiment actually tests its selected assumption.

# For example, your Experiment 18 asks students to choose between a free healthy meal and paid alternatives. Because the healthy meal is free, the results won't reliably show whether students would pay for it.

# Our next goal: make experiment generation produce tests that directly measure the assumption being evaluated.

# Open `experiments.py` and find the prompt inside `generate_experiment()`.

# Please paste that prompt here. I'll help you make a targeted change without disturbing the rest of your working code.