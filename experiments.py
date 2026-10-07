from llm import client
from models import Experiment


def generate_experiment(assumption):

    prompt = f"""
You are the experiment design component of LaunchProof AI.

Your job is to design a small, cheap, practical real-world
experiment to test the following business assumption.

ASSUMPTION:
{assumption}

Rules:

1. The experiment must directly test the assumption.
2. It must work for any type of business.
3. Prefer real customer behavior over opinions or surveys.
4. Keep the experiment small and inexpensive.
5. Define a measurable metric that directly tests the assumption.
6. Do not invent facts, costs, prices, market data, or evidence.
7. Do not assume unknown business inputs.
8. If a cost is unknown, do not create a fake number.
9. The experiment should measure the assumption itself, not a different assumption.
10. Return ONLY valid JSON.
11. The success metric must be measurable using actual experiment results.
12. If the experiment cost cannot be determined from the information provided,
    set estimated_cost to null rather than 0.
13. Do not invent the number of customers, users, units, or participants
    unless it is explicitly provided or clearly presented as a proposed
    experimental sample size.
14. Do not describe an invented sample size as evidence.   
15. Do not invent a success threshold such as "30% or higher"
    unless the threshold is explicitly provided in the assumption,
    business requirements, or experiment context.

16. If no justified success threshold is available, describe
    only what will be measured.

17. Do not label an arbitrary conversion rate, revenue level,
    satisfaction score, or number of customers as "success"
    without a provided basis.

18. The success_metric field should describe the measurement,
    not make the final business decision.
19. If the experiment specifies a planned number of participants,
  return that number in planned_sample_size.
20. planned_sample_size must represent the number of participants
  or experimental units explicitly planned for the experiment.
21. If no planned sample size is specified, return null.
22.  Do not invent a planned sample size.
    
Return exactly this structure:

{{
    "assumption": "...",
    "experiment": "...",
    "success_metric": "...",
    "estimated_cost": null,
    "duration": "...",
    "planned_sample_size": 30
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

    return Experiment.model_validate_json(result)

