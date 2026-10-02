"""
Data Models for Tax Due Diligence and Contingent Liability Materialization.
Aligns with Ind AS 37 / AS 29 accounting standards and Indian Judicial Hierarchy.
"""

from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class TaxType(str, Enum):
    DIRECT_TAX = "Direct Tax"
    INDIRECT_TAX_GST = "Indirect Tax (GST)"

class IndAS37Status(str, Enum):
    PROBABLE = "Probable (> 50% - Provision Required)"
    POSSIBLE = "Possible (10% to 50% - Contingent Liability Disclosure)"
    REMOTE = "Remote (< 10% - No Disclosure Required)"

class CourtHierarchy(str, Enum):
    SUPREME_COURT = "Supreme Court"
    JURISDICTIONAL_HC = "Jurisdictional High Court"
    NON_JURISDICTIONAL_HC = "Non-Jurisdictional High Court"
    ITAT_SPECIAL_BENCH = "ITAT Special Bench"
    ITAT_DIVISION_BENCH = "ITAT Division Bench"
    APPELLATE_AUTHORITY = "Appellate Authority (CIT-A / GST-AA)"

class PrecedentCase(BaseModel):
    id: str
    case_title: str
    citation: str
    court: str
    hierarchy_level: str
    year: int
    tax_type: str
    sections: List[str]
    subject: str
    department_position: str
    assessee_position: str
    ratio_decidendi: str
    favorable_to: str  # "Revenue" or "Assessee"
    pro_revenue_score: float = Field(ge=0.0, le=1.0)
    key_distinguishing_factors: List[str]
    applicable_states: List[str] = Field(default_factory=lambda: ["All India"])

class TaxLitigation(BaseModel):
    id: str
    company_name: str
    assessment_year: str
    tax_type: str
    dispute_type: str
    sections: List[str]
    forum: str
    jurisdiction_state: str
    disputed_base_demand: float
    demand_notice_date: str
    facts_summary: str
    department_arguments: str
    company_arguments: str
    status: str
    pre_deposit_paid: float = 0.0

class PrecedentMatch(BaseModel):
    precedent: PrecedentCase
    relevance_score: float  # 0 to 1
    binding_authority: str  # "Binding Law of the Land", "Jurisdictional Binding", "Persuasive Authority"
    distinguishing_risk: str  # Low, Medium, High risk of court distinguishing company's facts
    net_impact: str  # "Favorable to Assessee", "Adverse / Pro-Revenue", "Neutral"
    weighted_crystallization_score: float

class ExposureBreakdown(BaseModel):
    base_tax_demand: float
    interest_amount: float
    interest_breakdown: Dict[str, float]
    penalty_estimated_min: float
    penalty_estimated_max: float
    penalty_recommended: float
    total_gross_exposure: float
    pre_deposit_paid: float
    remaining_cash_at_risk: float
    appeal_stay_deposit_needed: float

class DealRecommendation(BaseModel):
    accounting_treatment: IndAS37Status
    ebitda_adjustment_recommended: bool
    net_debt_deduction_amount: float
    specific_indemnity_needed: bool
    escrow_holdback_suggested: float
    deal_negotiation_memo: str

class AssessmentResult(BaseModel):
    litigation: TaxLitigation
    crystallization_probability: float  # Percentage 0 to 100
    ind_as_37_classification: IndAS37Status
    court_hierarchy_weight: float
    matching_precedents: List[PrecedentMatch]
    exposure: ExposureBreakdown
    deal_recommendation: DealRecommendation
    key_risk_drivers: List[str]
    mitigating_factors: List[str]
