from typing import Literal

from pydantic import BaseModel

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
    statement : str
    importance : Literal["Low","Medium","High"]
    evidence : str
    evaluation : EvidenceEvaluation
    confidence : Literal["Low","Medium","High"]
    risk : Literal["Low","Medium","High"]
    
    
class AssumptionList(BaseModel):
    assumptions : list[Assumption]
    
