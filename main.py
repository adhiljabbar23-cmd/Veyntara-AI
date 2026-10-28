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
from experiment_results import apply_experiment_result,build_economic_threshold
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
    update_experiment_result,
    update_business_variable_cost
)

initialize_database()


def view_existing_business(business_id):
    business = get_business(business_id)

    if business is None:
        print("Business not found.")
        return

    print("\n========== BUSINESS DETAILS ==========")
    print(f"ID: {business[0]}")
    print(f"Name: {business[1]}")
    print(f"Idea: {business[2]}")
    print(f"Target customer: {business[3]}")
    print(f"Location: {business[4]}")
    print(f"Price: ₹{business[5]}")
    print(f"Variable cost: ₹{business[6]}")
    print(f"Revenue model: {business[7]}")
    print(f"Initial budget: ₹{business[8]}")

    assumptions = get_assumptions(business_id)
    experiments = get_experiments(business_id)

    print("\n========== SAVED ASSUMPTIONS ==========")

    if assumptions:
        for assumption in assumptions:
            print(f"\nAssumption ID: {assumption[0]}")
            print(f"Statement: {assumption[1]}")
            print(f"Importance: {assumption[2]}")
            print(f"Evidence: {assumption[3]}")
            print(f"Risk: {assumption[4]}")
            print(f"Confidence: {assumption[5]}")
    else:
        print("No saved assumptions yet.")

    print("\n========== SAVED EXPERIMENTS ==========")

    if experiments:
        for experiment in experiments:
            print(f"\nExperiment ID: {experiment[0]}")
            print(f"Assumption ID: {experiment[1]}")
            print(f"Experiment: {experiment[2]}")
            print(f"Success metric: {experiment[3]}")
            print(f"Status: {experiment[11]}")
            print(f"Result: {experiment[7]}")
            print(f"Observations: {experiment[8]}")
            print(f"Outcome assessment: {experiment[12] if len(experiment) > 12 else None}")
    else:
        print("No saved experiments yet.")




def run_workflow():
    print("\n1. Create a new business")
    print("2. Continue an existing business")
    print("3. Exit")

    choice = input("\nChoose an option: ").strip()

    if choice == "3":
        print("Goodbye!")
        raise SystemExit
    elif choice == "2":
        businesses = get_all_businesses()

        if not businesses:
            print("\nNo existing businesses found.")
            return

        print("\nExisting businesses:")


        for item in businesses:
            print(
                f"ID: {item[0]} | Name: {item[1]} | "
                f"Idea: {item[2]} | Location: {item[3]}"
            )

        try:
            selected_id = int(
                input("\nEnter the business ID to continue: ").strip()
            )
        except ValueError:
            print("Invalid ID. Please enter a number.")
            return


        business_id = selected_id
        existing_business = get_business(business_id)

        if existing_business is None:
            print("\nBusiness not found.")
            return

        stored_variable_cost = existing_business[6]
        if stored_variable_cost is None:
            print("\nThis older business record has no variable cost saved.")
            print("Enter the real variable cost per unit, or press Enter to cancel.")
            variable_cost_input = input("Variable cost per unit (₹): ").strip()

            if not variable_cost_input:
                print("Cancelled. No database records were changed.")
                return

            try:
                stored_variable_cost = float(variable_cost_input)
                if stored_variable_cost < 0:
                    raise ValueError
            except ValueError:
                print("Please enter a valid non-negative number. No records were changed.")
                return

            update_business_variable_cost(business_id, stored_variable_cost)
            existing_business = get_business(business_id)

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

        print(f"\nContinuing business: {business.name}")

        existing_assumptions = get_assumptions(business_id)

        print("\nExisting assumptions:")



        # Get all experiments for this business
        previous_experiments = get_experiments(business_id)

        # Group experiments by their assumption ID
        experiments_by_assumption = {}

        for experiment in previous_experiments:
            assumption_id = experiment[1]

            experiments_by_assumption.setdefault(
                assumption_id, []
            ).append(experiment)

        # Display existing assumptions
        for assumption in existing_assumptions:
            print(
                f"ID: {assumption[0]} | "
                f"Importance: {assumption[2]} | "
                f"Risk: {assumption[4]} | "
                f"Confidence: {assumption[5]}"
            )
        # Find assumptions that still need validation
        planned_candidates = []
        unevaluated_candidates = []

        for assumption in existing_assumptions:
            assumption_id = assumption[0]
            assumption_experiments = experiments_by_assumption.get(
                assumption_id, []
            )

            planned_for_assumption = [
                experiment
                for experiment in assumption_experiments
                if experiment[11] == "planned"
            ]

            if planned_for_assumption:
                planned_candidates.append(assumption)
                continue

            needs_evaluation = (
                assumption[4] is None
                or assumption[5] is None
                or assumption[5] == "Low"
            )

            if needs_evaluation:
                unevaluated_candidates.append(assumption)

        # Combine both groups so manual selection can see all eligible assumptions.
        # Planned-experiment assumptions will still be prioritized below.
        candidates = planned_candidates + [
            assumption
            for assumption in unevaluated_candidates
            if assumption not in planned_candidates
        ]

        if not candidates:
            print("\nNo assumptions currently need validation.")
            return

        # Prioritize assumptions with planned experiments first,
        # then importance: High, Medium, Low.
        importance_order = {
            "High": 0,
            "Medium": 1,
            "Low": 2
        }

        candidates.sort(
            key=lambda assumption: (
                0 if any(
                    experiment[11] == "planned"
                    for experiment in experiments_by_assumption.get(
                        assumption[0], []
                    )
                ) else 1,
                importance_order.get(assumption[2], 3)
            )
        )



        # Keep automatic prioritization as the default, but allow manual selection.
        recommended_assumption = candidates[0]

        print("\nAssumptions available for validation:")
        for index, assumption in enumerate(candidates, start=1):
            has_planned_experiment = any(
                experiment[11] == "planned"
                for experiment in experiments_by_assumption.get(assumption[0], [])
            )
            planned_label = " | Planned experiment exists" if has_planned_experiment else ""
            print(
                f"{index}. Assumption ID: {assumption[0]} | "
                f"Importance: {assumption[2]}{planned_label}\n"
                f"   {assumption[1]}"
            )

        print("\nPress Enter to use the recommended assumption, or enter a number to choose another.")
        selection = input("Assumption choice: ").strip()

        if not selection:
            next_assumption = recommended_assumption
            print("\nUsing the recommended assumption.")
        else:
            try:
                selected_index = int(selection)
            except ValueError:
                print("Invalid choice. Returning to the main menu.")
                return

            if not 1 <= selected_index <= len(candidates):
                print("Invalid choice. Returning to the main menu.")
                return

            next_assumption = candidates[selected_index - 1]

        print("\nNext assumption to validate:")
        print(f"ID: {next_assumption[0]}")
        print(f"Statement: {next_assumption[1]}")
        print(f"Importance: {next_assumption[2]}")

        # Get experiments for the selected assumption only
        assumption_experiments = experiments_by_assumption.get(
            next_assumption[0], []
        )



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
            # Show planned experiments from newest to oldest
            planned_experiments.sort(
                key=lambda experiment: experiment[0],
                reverse=True
            )

            print("\nPlanned experiments available:")

            for index, experiment in enumerate(
                planned_experiments, start=1
            ):
                print(f"\n{index}. Experiment ID: {experiment[0]}")
                print(f"   Experiment: {experiment[2]}")
                print(f"   Success metric: {experiment[3]}")

            try:
                experiment_choice = int(
                    input("\nChoose an option number (1 to select an experiment): ").strip()
                )
            except ValueError:
                print("Invalid choice. Please enter a number.")
                return

            if not 1 <= experiment_choice <= len(planned_experiments):
                print("Invalid selection. Choose one of the displayed option numbers.")
                return

            latest_experiment = planned_experiments[
                experiment_choice - 1
            ]

        else:
            if assumption_experiments:
                print("\nNo planned experiment remains for this assumption.")
                print("Existing experiments are preserved; no duplicate will be created automatically.")
                print("1. Create a new follow-up experiment")
                print("2. Return to the main menu")
                followup_choice = input("Choose an option: ").strip()

                if followup_choice != "1":
                    print("No new experiment created. Existing records were not changed.")
                    return

            print("\nGenerating a new validation experiment...")

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
                return


            conducted = input(
                "\nHave you actually conducted this experiment? (y/n): "
            ).strip().lower()

            if conducted != "y":
                print("No results recorded. The experiment remains planned.")
                return

            result_text = input(
                "What happened in the experiment? "
            ).strip()

            observations = input(
                "What did you observe? "
            ).strip()

            real_data_confirm = input(
                "Are these actual experiment findings, not fictional test/example data? (y/n): "
            ).strip().lower()
            if real_data_confirm != "y":
                print("No results saved. The experiment remains planned.")
                print("You can test the workflow using a separate temporary database.")
                return

            print("\nOutcome assessment:")
            print("1. Met")
            print("2. Partially met")
            print("3. Not met")
            print("4. Inconclusive / not enough evidence")
            assessment_choices = {
                "1": "Met",
                "2": "Partially met",
                "3": "Not met",
                "4": "Inconclusive",
            }
            assessment_choice = input("Choose an outcome (1-4): ").strip()

            if assessment_choice not in assessment_choices:
                print("Invalid assessment. No results were saved; the experiment remains planned.")
                return

            outcome_assessment = assessment_choices[assessment_choice]

            if not result_text and not observations and outcome_assessment != "Inconclusive":
                print("Empty results can only be classified as Inconclusive.")
                print("No results were saved. Please record actual observations first.")
                return

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
                successes=successes,
                outcome_assessment=outcome_assessment
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
                business_threshold=threshold,
                business=business
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

            print("\nExperiment result and outcome assessment saved to database.")
            print(f"Outcome assessment: {outcome_assessment}")


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
            print(
                "Outcome assessment: "
                f"{latest_experiment[12] if len(latest_experiment) > 12 else None}"
            )
            print("No new experiment was created.")



    elif choice == "1":
        name = input("Business name: ").strip()
        idea = input("Business idea: ").strip()
        target_customer = input("Target customer: ").strip()
        location = input("Business location: ").strip()
        price = float(input("Selling price per unit: ₹"))
        variable_cost = float(input("Variable cost per unit: ₹"))
        revenue_model = input("Revenue model: ").strip()
        initial_budget = float(input("Initial budget: ₹"))

        business = BusinessProfile(
            name=name,
            idea=idea,
            target_customer=target_customer,
            location=location,
            price=price,
            variable_cost=variable_cost,
            revenue_model=revenue_model,
            initial_budget=initial_budget
        )


        business_saved = False
        cancelled = False

        existing_businesses = get_all_businesses()

        duplicate_found = any(
            existing[1].strip().casefold() == name.strip().casefold()
            and existing[2].strip().casefold() == idea.strip().casefold()
            for existing in existing_businesses
        )

        if duplicate_found:
            print(
                "\nA business with the same name and idea "
                "already exists."
            )
            print("\nWhat would you like to do?")
            print("1. Continue with an existing business")
            print("2. Cancel and return to the main menu")

            action = input("Choose an option: ").strip()

            if action == "1":
                print("\nExisting businesses:")

                for item in existing_businesses:
                    print(
                        f"ID: {item[0]} | Name: {item[1]} | "
                        f"Idea: {item[2]} | Location: {item[3]}"
                    )

                try:
                    selected_id = int(
                        input("\nEnter the business ID: ").strip()
                    )
                except ValueError:
                    print("Invalid ID. Returning to the menu.")
                else:
                    selected_business = get_business(selected_id)

                    if selected_business is None:
                        print("Invalid business ID. Returning to the menu.")
                    else:
                        business_id = selected_business[0]

                        selected_variable_cost = selected_business[6]
                        if selected_variable_cost is None:
                            print("\nThis older business record has no variable cost saved.")
                            print("Enter the real variable cost per unit, or press Enter to cancel.")
                            variable_cost_input = input("Variable cost per unit (₹): ").strip()

                            if not variable_cost_input:
                                print("Cancelled. No database records were changed.")
                                return

                            try:
                                selected_variable_cost = float(variable_cost_input)
                                if selected_variable_cost < 0:
                                    raise ValueError
                            except ValueError:
                                print("Please enter a valid non-negative number. No records were changed.")
                                return

                            update_business_variable_cost(business_id, selected_variable_cost)
                            selected_business = get_business(business_id)

                        business = BusinessProfile(
                            name=selected_business[1],
                            idea=selected_business[2],
                            target_customer=selected_business[3],
                            location=selected_business[4],
                            price=selected_business[5],
                            variable_cost=selected_business[6],
                            revenue_model=selected_business[7],
                            initial_budget=selected_business[8]
                        )

                        business_saved = True

                        print(f"\nSelected business ID: {business_id}")
                        print(f"Business: {business.name}")
                        print("Continuing with the selected business.")

            elif action == "2":
                print("Cancelled. No database records were changed.")
                return

            else:
                print("Invalid option. Returning to the menu.")
                return

        else:
            try:
                business_id = save_business(business)
                business_saved = True
                print(f"\nBusiness saved with ID: {business_id}")

            except ValueError as error:
                print(f"\n{error}")
                print("No new business was saved.")

        if not business_saved:
            print("Skipping assumption generation.")
        else:




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
                return

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

                        return

                    result_text = input("What actually happened? ").strip()
                    observations = input("What did you observe? ").strip()

                    real_data_confirm = input(
                        "Are these actual experiment findings, not fictional test/example data? (y/n): "
                    ).strip().lower()
                    if real_data_confirm != "y":
                        # Preserve the planned experiment, but do not save unverified results.
                        experiment_id = save_experiment(
                            business_id=business_id,
                            assumption_id=top_assumption_id,
                            experiment=experiment,
                            experiment_result=None
                        )
                        print("No results saved. The experiment remains planned.")
                        print(f"Experiment saved with ID: {experiment_id}")
                        print("You can test the workflow using a separate temporary database.")
                        return

                    print("\nOutcome assessment:")
                    print("1. Met")
                    print("2. Partially met")
                    print("3. Not met")
                    print("4. Inconclusive / not enough evidence")
                    assessment_choices = {
                        "1": "Met",
                        "2": "Partially met",
                        "3": "Not met",
                        "4": "Inconclusive",
                    }
                    assessment_choice = input("Choose an outcome (1-4): ").strip()
                    if assessment_choice not in assessment_choices:
                        experiment_id = save_experiment(
                            business_id=business_id,
                            assumption_id=top_assumption_id,
                            experiment=experiment,
                            experiment_result=None
                        )
                        print("Invalid assessment. No results saved; the experiment remains planned.")
                        print(f"Experiment saved with ID: {experiment_id}")
                        return

                    outcome_assessment = assessment_choices[assessment_choice]
                    if not result_text and not observations and outcome_assessment != "Inconclusive":
                        experiment_id = save_experiment(
                            business_id=business_id,
                            assumption_id=top_assumption_id,
                            experiment=experiment,
                            experiment_result=None
                        )
                        print("Empty results can only be classified as Inconclusive.")
                        print("No results saved. Please record actual observations first.")
                        print(f"Experiment saved with ID: {experiment_id}")
                        return

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
                        successes=successes,
                        outcome_assessment=outcome_assessment
                    )


                    contribution_per_unit = (
                        business.price - business.variable_cost
                    )

                    if contribution_per_unit <= 0:
                        print(
                            "\nCannot calculate a purchase threshold: "
                            "price must exceed variable cost."
                        )
                        return

                    # Do not invent the number of reachable customers.
                    reachable_customers_input = input(
                        "\nHow many eligible customers can this experiment "
                        "reasonably reach? Enter a supported estimate: "
                    ).strip()

                    try:
                        reachable_customers = int(reachable_customers_input)

                        if reachable_customers <= 0:
                            raise ValueError

                    except ValueError:
                        print(
                            "\nA positive whole-number estimate is required "
                            "to calculate an economic purchase threshold."
                        )
                        return

                    threshold = build_economic_threshold(
                        required_contribution=business.initial_budget,
                        contribution_per_unit=contribution_per_unit,
                        reachable_customers=reachable_customers
                    )


                    updated = apply_experiment_result(
                        assumption=top_assumption_object,
                        experiment=experiment,
                        experiment_result=experiment_result,
                        business_threshold=threshold,
                        business=business
                    )

                    # Persist the updated risk/confidence, matching the existing-experiment path.
                    update_assumption_evaluation(
                        assumption_id=top_assumption_id,
                        risk=updated["decision"]["risk"],
                        confidence=updated["decision"]["confidence"]
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
        return

while True:
    run_workflow()
