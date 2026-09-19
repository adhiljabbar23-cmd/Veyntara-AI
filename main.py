from models import BusinessProfile,AssumptionList
from agent import ask_ai

business = BusinessProfile(
    name = "FreshBite",
    idea = "Healthy meal delivery for college students",
    target_customer = "college students",
    location = "Kochi",
    price = 120,
    revenue_model="per-meal purchase",
    initial_budget=50000
    )



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
- evaluation
- confidence
- risk


Rules:

1. Do NOT invent evidence.

2. If evidence is unavailable, say:
   "Evidence not yet available."

3. Use the search_web tool when external information
   could help investigate an assumption.

4. After finding evidence for an important assumption,
   use the evaluate_evidence tool to determine whether
   the evidence supports, contradicts, or is unclear.

5. Do not automatically treat search results as valid
   evidence.

6. If evidence is indirect or does not directly answer
   the assumption, treat it as "Unclear".

7. Use the evidence evaluation when deciding confidence
   and risk.

8. Do not search for every possible piece of information.
   Prioritize the most important assumptions.

9. If useful evidence cannot be found, stop searching
   and mark the evidence as:
   "Evidence not yet available."

10. Do not treat a competitor's selling price as evidence
    of their production cost.

11. Confidence must be exactly one of:
    "Low", "Medium", "High".

12. Risk must be exactly one of:
    "Low", "Medium", "High".

13. Importance must be exactly one of:
    "Low", "Medium", "High".

14. The evaluation field must contain the result of the
    evaluate_evidence tool.

15. Do not invent the evaluation.

16. If evidence was evaluated, copy the evaluation result
    into the final JSON.

17. If evidence is not available, use:
    "relevance": "Low",
    "support": "Unclear",
    "strength": "Weak",
    and explain that evidence is not yet available.

18. After evaluating the evidence for the most important
    assumptions, STOP using tools.

19. You do not need to investigate every assumption.
    If evidence is unavailable after a reasonable search,
    mark it as "Evidence not yet available" and move on.

20. Once you have enough information to produce the
    5 assumptions, immediately return the final JSON.

21. Never continue searching indefinitely.

22. Return ONLY valid JSON.



The JSON must follow this exact structure:

{{
    "assumptions": [
        {{
            "statement": "...",
            "importance": "High",
            "evidence": "...",
            "evaluation": {{
                "relevance": "High",
                "support": "Supports",
                "strength": "Moderate",
                "explanation": "..."
            }},
            "confidence": "Low",
            "risk": "High"
        }}
    ]
}}

"""
answer = ask_ai(question)

print("\nRaw AI Response")
print(answer)

if answer == "The agent reached its research limit.":
    print("\nThe agent did not finish within the research limit.")
    
else:    
    assumptions = AssumptionList.model_validate_json(answer)

    print("\nValidated Response")
    print(assumptions)

