from llm import client
from models import ModificationRecommendation

def generate_modification(assumption, experiment_result, decision):

    prompt = f"""
You are the modification recommendation component of Veyntara AI.

The business validation system has decided:

DECISION:
{decision}

ASSUMPTION:
{assumption.statement}

EXPERIMENT RESULT:
{experiment_result.result}

OBSERVATIONS:
{experiment_result.observations}

Your job is to recommend what part of the business should be
modified before running another experiment.

Rules:

1. Base the recommendation ONLY on the experiment evidence.
2. Do not invent customer preferences or business facts.
3. Identify the specific part of the assumption that should change.
4. Explain why the modification is justified by the evidence.
5. Suggest a concrete modification.
6. Suggest what the next experiment should test.
7. Do not make the final business decision.
8. Do not invent a specific new price, discount, feature,
   customer segment, or business change unless the experiment
   evidence directly supports that specific change.
9. If the evidence only supports a general direction,
   describe the modification at that level.
   For example, say "test a lower price" rather than
   suggesting ₹90 or ₹100.
10. Return ONLY valid JSON.

Return exactly:

{{
    "problem": "...",
    "evidence": "...",
    "modification": "...",
    "reason": "...",
    "next_experiment": "..."
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

    print("\nModification Recommendation:")
    print(result)

    return ModificationRecommendation.model_validate_json(result)