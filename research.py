from models import EvidenceEvaluation
from llm import client


def evaluate_evidence(assumptions):

    print("\nEvaluating evidence...")

    formatted_evidence = ""

    for i, item in enumerate(assumptions, start=1):
        formatted_evidence += f"""
ASSUMPTION {i}:
{item["statement"]}

EVIDENCE {i}:
{item["evidence"]}
"""

    prompt = f"""
You are an evidence evaluation component of LaunchProof AI.

Evaluate the evidence for each business assumption.

{formatted_evidence}

For each assumption, determine:

- relevance: Low, Medium, or High
- support: Supports, Contradicts, or Unclear
- strength: Weak, Moderate, or Strong
- explanation: short explanation

Rules:

1. Evaluate ONLY the evidence provided.
2. Do not invent information.
3. Do not assume that a selling price represents production cost.
4. If the evidence does not directly answer the assumption,
   mark support as "Unclear".
5. Indirect evidence should normally be treated as "Unclear".
6. Do not confuse market size with actual customer demand.
7. Return one evaluation for every assumption.
8. Keep the same order as the assumptions.
9. Return ONLY valid JSON.

Return exactly:

{{
    "evaluations": [
        {{
            "relevance": "High",
            "support": "Supports",
            "strength": "Moderate",
            "explanation": "..."
        }}
    ]
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

    print("\nEvidence evaluations:")
    print(result)

    # Remove Markdown code fences if the model adds them
    if result.startswith("```"):
        result = result.strip()
        result = result.removeprefix("```json")
        result = result.removeprefix("```")
        result = result.removesuffix("```")
        result = result.strip()

    return result