from typing import Literal

from pydantic import BaseModel,Field

class BusinessProfile(BaseModel):
    name : str
    idea : str
    target_customer : str
    location : str
    price : float
    revenue_model : str
    initial_budget : float
    
class EvidenceEvaluation(BaseModel):
    relevance : Literal["Low", "Medium", "High"]
    support : Literal["Supports", "Contradicts", "Unclear"]
    strength : Literal["Weak", "Moderate", "Strong"]
    explanation : str
    

class Assumption(BaseModel):
    statement: str
    importance: Literal["Low", "Medium", "High"]
    evidence: str
    evaluation: EvidenceEvaluation | None = None
    

class AssumptionList(BaseModel):
    assumptions : list[Assumption]
    
class Experiment(BaseModel):
    assumption: str
    experiment: str
    success_metric: str
    estimated_cost: float | None
    duration: str
    planned_sample_size: int | None = None


class ExperimentResult(BaseModel):
    experiment: str
    result: str | None = None
    observations: str | None = None
    sample_size: int | None = None
    successes: int | None = None
    
    
class ExperimentAnalysis(BaseModel):
    support: Literal["Supports", "Contradicts", "Unclear"]
    strength: Literal["Weak", "Moderate", "Strong"]
    evidence: str
    explanation: str
    
class EconomicThresholdBasis(BaseModel):
    required_contribution: float = Field(gt=0)
    contribution_per_unit: float = Field(gt=0)
    reachable_customers: int = Field(gt=0)
    
class BusinessThreshold(BaseModel):
    metric: str
    value: float = Field(ge=0, le=1)

    source: Literal[
        "user_defined",
        "derived_from_economics",
        "external_requirement"
    ]

    rationale: str

    economic_basis: EconomicThresholdBasis | None = None
    
class ThresholdEvaluation(BaseModel):
    strength: Literal["Weak", "Moderate", "Strong"]
    valid: bool
    explanation: str
    

class StatisticalResult(BaseModel):
    sample_size: int
    successes: int
    observed_rate: float
    threshold: float
    confidence_interval: tuple[float, float]
    confidence_level: float
    p_value: float
    significance_level: float
    statistically_significant: bool
    
class BusinessSignificance(BaseModel):
    required_rate: float
    observed_rate: float
    confidence_interval: tuple[float, float]
    classification: Literal[
        "Above Threshold",
        "Uncertain",
        "Below Threshold"
    ]
    explanation: str
    
class ModificationRecommendation(BaseModel):
    problem: str
    evidence: str
    modification: str
    reason: str
    next_experiment: str