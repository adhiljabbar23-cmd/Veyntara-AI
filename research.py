

from models import EvidenceEvaluation
from llm import client

def evaluate_evidence(assumption, evidence):

    print("\nEvaluating evidence...")
    print("Assumption:", assumption)
    
    prompt = f"""
    
    You are an evidence evaluation component of LaunchProof AI.

Evaluate whether the provided evidence actually supports
the business assumption.

ASSUMPTION:
{assumption}

EVIDENCE:
{evidence}

Evaluate the evidence using these fields:

- relevance: Low, Medium, or High
- support: Supports, Contradicts, or Unclear
- strength: Weak, Moderate, or Strong
- explanation: short explanation

Rules:

1. Do not invent information.
2. Judge only the evidence provided.
3. Do not assume that a selling price represents production cost.
4. If the evidence does not directly answer the assumption,
   mark support as "Unclear".
5. Return ONLY valid JSON.

Return exactly:

{{
    "relevance": "High",
    "support": "Supports",
    "strength": "Moderate",
    "explanation": "..."
}}"""
    
    response = client.chat.completions.create(
        model = "openai/gpt-oss-20b",
        messages = [
            {
                "role" : "user",
                "content" : prompt
            }
        ]
    )
    
    result = response.choices[0].message.content
    
    print("Evidence evaluation:", result)
    
    return EvidenceEvaluation.model_validate_json(result)

