from models import Assumption


def evaluate_assumption(assumption: Assumption):

    evaluation = assumption.evaluation

    if evaluation.support == "Unclear":

        risk = "Unknown"

    elif evaluation.support == "Contradicts":

        if evaluation.strength in ["Strong", "Moderate"]:
            risk = "High Risk"
        else:
            risk = "Medium Risk"

    elif evaluation.support == "Supports":

        if evaluation.strength == "Strong":
            risk = "Low Risk"

        elif evaluation.strength == "Moderate":
            risk = "Medium Risk"

        else:
            risk = "Unknown"

    else:

        risk = "Unknown"

    confidence = calculate_confidence(assumption)

    return {
        "statement": assumption.statement,
        "importance": assumption.importance,
        "risk": risk,
        "confidence": confidence,
        "relevance": evaluation.relevance,
        "support": evaluation.support,
        "strength": evaluation.strength,
        "explanation": evaluation.explanation
    }
    
    

def evaluate_all_assumptions(assumptions):

    results = []

    for assumption in assumptions:

        result = evaluate_assumption(assumption)

        results.append(result)

    return results

IMPORTANCE_WEIGHTS = {
    "Low" : 1,
    "Medium" : 2,
    "High" : 3 
}

RISK_SCORES = {
    "Low Risk": 0,
    "Medium Risk": 1,
    "High Risk": 2,
    "Unknown": 0
}

CONFIDENCE_WEIGHTS = {
    "High": 0,
    "Medium": 1,
    "Low": 2
}

PRIORITY_RISK_WEIGHTS = {
    "Low Risk": 0,
    "Medium Risk": 2,
    "High Risk": 3,
    "Unknown": 3
}

def calculate_overall_risk(results):
    total_risk = 0
    total_weight = 0

    for result in results:
        # Unknown means insufficient evidence,
        # so don't treat it as either risk or safety.
        if result["risk"] == "Unknown":
            continue

        importance_weight = IMPORTANCE_WEIGHTS[result["importance"]]
        risk_score = RISK_SCORES[result["risk"]]

        total_risk += importance_weight * risk_score
        total_weight += importance_weight

    if total_weight == 0:
        return 0

    return total_risk / total_weight

def calculate_uncertainty(results):
    unknown_count = 0

    for result in results:
        if result["risk"] == "Unknown":
            unknown_count += 1

    return unknown_count

def find_critical_risks(results):
    
    critical_risks = []
    
    for result in results:
        
        if (
            result["importance"] == "High"
            and result["risk"] == "High Risk"
        ):
            critical_risks.append(result)
            
    return critical_risks

def find_unknowns(results):
    
    unknowns = []
    
    for result in results:
        
        if (
            result["importance"] == "High"
            and result["risk"] == "Unknown"
        ):
            unknowns.append(result)
            
    return unknowns


def make_decision(results):

    critical_risks = find_critical_risks(results)
    unknowns = find_unknowns(results)
    evidence_gaps = find_evidence_gaps(results)
    priority_assumptions = find_priority_assumptions(results)
    overall_risk = calculate_overall_risk(results)
    uncertainty_count = calculate_uncertainty(results)
    
    # 1. Strong contradictory evidence on a critical assumption
    strong_contradictions = [
        result for result in results
        if (
            result["importance"] == "High"
            and result["risk"] == "High Risk"
            and result["strength"] == "Strong"
        )
    ]

    # 2. Moderate contradiction means the business may need modification
    moderate_contradictions = [
        result for result in results
        if (
            result["importance"] == "High"
            and result["risk"] == "High Risk"
            and result["strength"] == "Moderate"
        )
    ]

    if strong_contradictions:
        decision = "Don't Launch"
        reason = (
            "A high-importance assumption has strong contradictory "
            "evidence, indicating that the current business model "
            "has a critical problem."
        )

    elif moderate_contradictions:
        decision = "Modify"
        reason = (
            "A high-importance assumption has contradictory evidence, "
            "but the evidence is not strong enough to reject the entire "
            "business. The affected part of the business should be modified "
            "and tested again."
        )

    elif unknowns:
        decision = "Test More"
        reason = (
            "One or more high-importance assumptions are still "
            "unvalidated."
        )

    elif overall_risk >= 1:
        decision = "Modify"
        reason = (
            "The available evidence indicates meaningful business risk "
            "that should be addressed before launch."
        )

    else:
        decision = "Launch"
        reason = (
            "The important assumptions have sufficient supporting evidence "
            "and no critical risks were identified."
        )

    return {
        "decision": decision,
        "reason": reason,
        "overall_risk": overall_risk,
        "uncertainty_count": uncertainty_count,
        "critical_risks": critical_risks,
        "evidence_gaps": evidence_gaps,
        "priority_assumptions": priority_assumptions
    } 
        
def find_evidence_gaps(results):

    gaps = []

    for result in results:

        if result["risk"] == "Unknown":

            gaps.append({
                "statement": result["statement"],
                "importance": result["importance"],
                "reason": result["explanation"]
            })

    return gaps


def calculate_confidence(assumption: Assumption):

    evaluation = assumption.evaluation

    if evaluation.support == "Unclear":
        return "Low"

    if evaluation.relevance == "Low":
        return "Low"

    if (
        evaluation.relevance == "High"
        and evaluation.strength == "Strong"
    ):
        return "High"

    if (
        evaluation.relevance in ["High", "Medium"]
        and evaluation.strength == "Moderate"
    ):
        return "Medium"

    return "Low"


def calculate_priority(result):

    importance_score = IMPORTANCE_WEIGHTS[
        result["importance"]
    ]

    risk_score = PRIORITY_RISK_WEIGHTS[
        result["risk"]
    ]

    uncertainty_score = CONFIDENCE_WEIGHTS[
        result["confidence"]
    ]

    priority_score = (
        importance_score
        + risk_score
        + uncertainty_score
    )

    return priority_score

def find_priority_assumptions(results):

    prioritized = []

    for result in results:

        score = calculate_priority(result)

        prioritized.append({
            "statement": result["statement"],
            "importance": result["importance"],
            "risk": result["risk"],
            "confidence": result["confidence"],
            "priority_score": score
        })

    prioritized.sort(
        key=lambda x: x["priority_score"],
        reverse=True
    )

    return prioritized

def update_assumption_evidence(
    assumption,
    evidence,
    evidence_evaluation
):

    updated_assumption = assumption.model_copy(
        deep=True
    )

    updated_assumption.evidence = evidence

    updated_assumption.evaluation = evidence_evaluation

    return updated_assumption

if __name__ == "__main__":

    from models import Assumption, EvidenceEvaluation

    assumption = Assumption(
        statement=(
            "There is sufficient demand for healthy meal delivery "
            "among college students."
        ),
        importance="High",
        evidence="Evidence not yet available.",
        evaluation=EvidenceEvaluation(
            relevance="Low",
            support="Unclear",
            strength="Weak",
            explanation="Evidence not yet available."
        )
    )

    new_evaluation = EvidenceEvaluation(
        relevance="High",
        support="Unclear",
        strength="Weak",
        explanation=(
            "The data shows that 34% of participants ordered at least once "
            "and 7 of those repeated an order within 14 days."
        )
    )

    new_evidence = (
        "11 paid orders out of 32 participants, "
        "with 7 customers placing another order within 14 days."
    )

    updated = update_assumption_evidence(
        assumption,
        new_evidence,
        new_evaluation
    )

    print("\nUpdated Assumption:")
    print(updated)

    print("\nUpdated Decision Analysis:")
    print(evaluate_assumption(updated))