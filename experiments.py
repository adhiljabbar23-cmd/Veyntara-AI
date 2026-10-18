from llm import client
from models import Experiment
from pydantic import ValidationError
import json



def generate_experiment(assumption):

    prompt = f"""
You are the experiment design component of Veyntara AI.

Your job is to design a small, inexpensive, practical real-world
experiment that directly tests a business assumption.

ASSUMPTION:
{assumption}

CORE RULES:

1. The experiment must directly test the given assumption.
2. Design experiments that work for different types of businesses.
3. Prefer observable customer behavior over opinions or surveys
   when practical.
4. Keep the experiment small, inexpensive, and feasible.
5. Define a measurable metric that directly tests the assumption.
6. Do not invent facts, costs, prices, market data, or evidence.
7. Do not assume unknown business inputs.
8. If a cost cannot be determined, set estimated_cost to null.
9. Do not test a different assumption from the one provided.
10. Return only valid JSON matching the required structure.
11. The metric must be measurable from the planned experiment.
12. Use null for unknown costs, never zero as a substitute.
13. A proposed sample size is a plan, not evidence.
14. Do not invent a success threshold without a justified basis.
15. If no justified threshold exists, describe what will be measured
    without declaring an arbitrary success target.
16. success_metric describes the measurement, not the final decision.

17. planned_sample_size must be either a positive integer or null.
18. Never put explanations, ranges, or text inside planned_sample_size.
19. If the experiment has no fixed, explicitly planned sample size,
    return null. Do not estimate a sample size from assumed footfall.
20. If a sample size is explicitly planned, return only the integer.
    For example, use 30, not "30 participants".


FAIRNESS AND VALIDITY RULES:

21. Ensure the experiment fairly tests the stated assumption.
22. When comparing alternatives, keep conditions comparable.
    Account for differences in price, portion size, availability,
    presentation, and other factors that could bias the result.
23. Never compare a free option against paid alternatives to infer
    product preference. If prices differ naturally, disclose and
    record those prices and interpret the results accordingly.
23. Distinguish stated preferences, clicks, sign-ups, purchase
    intentions, completed orders, and repeat purchases. They are
    different types of evidence.
25. Prefer actual purchases when testing willingness to pay,
    and actual repeated purchases when testing retention.
26. Do not claim that a customer behavior proves a broader
    assumption than the experiment can support.
27. Do not propose selling, spending, or collecting data in ways
    that exceed known budget constraints.
28. Do not invent business details that are missing from the
    assumption. If an essential input is unknown, design a test
    that can work without it or explicitly identify the limitation.
29. Make the experiment specific: explain what to do, who to test,
    what to record, and how the metric will be calculated.
30. Do not claim that an experiment has been conducted. This
    function creates a plan only; results must be recorded separately.


31. Never invent trial prices, discounts, menu items, locations,
    or other operational details as established facts. If an input
    is unknown, either make it an explicitly labeled proposal that
    requires user confirmation or design the experiment without
    depending on that unknown input. Do not claim that equal prices
    isolate preference if the proposed prices are arbitrary.


32. Preserve the exact comparison specified by the assumption.
    Do not replace named alternatives with unrelated control groups.
    If the assumption compares a product with local mess food and
    fast food, the experiment must compare against those alternatives.
    If a fair comparison is not feasible with the available inputs,
    explain the limitation instead of silently changing the comparison.

33. Do not invent actual selling prices. If prices are unknown,
    identify them as proposed values requiring user confirmation.
    Record the actual prices used when the experiment is conducted.


34. Define metrics that accurately represent the assumption.
    When comparing three alternatives, report each option's share
    of total purchases. Do not claim that one option is preferred
    overall merely because it outsells each alternative individually.
    Distinguish a descriptive result from a predefined success
    threshold. If no justified threshold exists, report the measured
    shares without declaring success or failure.


35. When practical, record both completed purchases and the number
    of eligible people exposed to the offer. Report purchase shares
    among completed transactions separately from the conversion rate
    among exposed people. Do not treat non-buyers as missing if they
    were exposed to the offer and their behavior can be recorded.


36. Define the measurement unit and denominator for every metric
    according to the type of experiment.

    Use the appropriate unit, such as unique people, businesses,
    transactions, users, tasks, API requests, or other relevant
    experimental units.

    Avoid double-counting repeated interactions when unique entities
    can be identified reliably.

    If an experiment measures conversion, define what counts as
    exposure and what counts as conversion.

    If an experiment measures performance, define the relevant
    input, output, and performance measure.

    If the required denominator or measurement cannot be collected
    reliably, report the metric as unavailable rather than inventing
    a value.

    Do not force customer conversion metrics onto experiments that
    measure technical performance, operational efficiency, or other
    non-customer outcomes.


37. Choose experimental conditions that match the business assumption.
    Do not automatically force equal prices or identical conditions
    when those conditions remove an important part of the real-world
    question. If price is part of the assumption, measure or record
    price-related behavior explicitly. Distinguish transactions,
    units sold, and unique customers, and use the unit that best
    supports the stated assumption.


38. Check experiment feasibility before recommending execution.
    Identify essential resources, permissions, costs, and operational
    requirements that are unknown. Do not assume they are available.
    Prefer a simpler experiment when it can test the same assumption
    with less cost and effort. Clearly identify any unresolved
    requirements that must be confirmed before execution.


39. Ensure conversion metrics use consistent counting units.
    For customer conversion, count unique eligible entities that
    complete at least one desired action divided by unique eligible
    entities exposed to the offer. Report transaction counts separately.
    Ensure the result cannot exceed 100% unless the metric is explicitly
    a rate that permits repeated events.

40. State when experimental conditions limit the conclusion.
    If prices, access, timing, or other conditions differ from normal
    real-world conditions, explain what the experiment can and cannot
    establish about the original assumption.


Return exactly this structure:

{{
    "assumption": "...",
    "experiment": "...",
    "success_metric": "...",
    "estimated_cost": null,
    "duration": "...",
    "planned_sample_size": null
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

    print("\nGenerated Experiment:")
    print(result)


    try:
        result = result.strip()

        # Remove Markdown code fences if present
        if result.startswith("```"):
            lines = result.splitlines()

            if lines and lines[0].startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            result = "\n".join(lines).strip()

        # Extract the JSON object, even if text comes before it
        decoder = json.JSONDecoder()
        json_start = result.find("{")

        if json_start == -1:
            raise ValueError(
                "AI response did not contain a JSON object."
            )

        parsed_json, _ = decoder.raw_decode(result[json_start:])

        return Experiment.model_validate(parsed_json)

    except (ValidationError, ValueError) as e:
        print("\nExperiment output did not match the required schema:")
        print(e)
        raise




