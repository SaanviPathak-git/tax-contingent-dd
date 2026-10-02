"""
Judicial Hierarchy Scoring and Ind AS 37 Materialization Engine.
Translates case law precedents, forum stages, and legal arguments into
a calibrated crystallization probability and M&A Due Diligence recommendations.
"""

from typing import List, Tuple
from core.models import (
    TaxLitigation,
    PrecedentMatch,
    IndAS37Status,
    DealRecommendation,
    AssessmentResult,
    ExposureBreakdown
)

class HierarchyScorer:
    """Evaluates the probability of a contingent liability crystallizing into an actual liability."""

    FORUM_STAGE_FACTORS = {
        "Assessing Officer (AO / Faceless AO)": 0.75,
        "Adjudicating Authority (GST)": 0.75,
        "Dispute Resolution Panel (DRP) / CIT(A)": 0.60,
        "GST Appellate Authority (Joint Commissioner Appeals)": 0.60,
        "Income Tax Appellate Tribunal (ITAT)": 0.45,
        "GST Appellate Tribunal (GSTAT)": 0.45,
        "High Court": 0.40,
        "Supreme Court of India": 0.50
    }

    @classmethod
    def evaluate_probability(
        cls,
        litigation: TaxLitigation,
        matches: List[PrecedentMatch],
        exposure: ExposureBreakdown
    ) -> AssessmentResult:
        risk_drivers: List[str] = []
        mitigating_factors: List[str] = []

        # 1. Base rate from forum stage
        forum_weight = 0.50
        for forum_key, weight in cls.FORUM_STAGE_FACTORS.items():
            if forum_key.lower() in litigation.forum.lower() or litigation.forum.lower() in forum_key.lower():
                forum_weight = weight
                break

        # 2. Precedent-driven probability calculation
        if not matches:
            # No direct precedents found, default to forum stage baseline
            calculated_prob = forum_weight * 100
            risk_drivers.append("No direct landmark judicial precedent identified on this specific issue.")
            court_hierarchy_wt = 0.5
        else:
            # Weighted average across matching precedents
            total_weight = 0.0
            weighted_prob_sum = 0.0
            
            has_binding_sc = False
            has_binding_jhc = False

            for match in matches:
                prec = match.precedent
                weight = match.relevance_score * (1.2 if "Supreme Court" in match.binding_authority else 0.9)
                total_weight += weight

                # Probability contribution
                case_prob = prec.pro_revenue_score * 100
                weighted_prob_sum += (case_prob * weight)

                if "Supreme Court" in match.binding_authority:
                    has_binding_sc = True
                    if prec.favorable_to == "Revenue":
                        risk_drivers.append(f"Adverse Supreme Court landmark ruling in '{prec.case_title}' ({prec.citation})")
                    else:
                        mitigating_factors.append(f"Highly favorable Supreme Court precedent in '{prec.case_title}' ({prec.citation})")
                elif "Jurisdictionally Binding" in match.binding_authority:
                    has_binding_jhc = True
                    if prec.favorable_to == "Revenue":
                        risk_drivers.append(f"Adverse Jurisdictional High Court ruling in '{prec.case_title}'")
                    else:
                        mitigating_factors.append(f"Favorable Jurisdictional High Court ruling in '{prec.case_title}'")

            court_hierarchy_wt = 1.0 if has_binding_sc else (0.85 if has_binding_jhc else 0.60)
            precedent_prob = (weighted_prob_sum / total_weight) if total_weight > 0 else 50.0

            # Combine precedent probability with forum factor (75% precedent weight, 25% forum factor)
            calculated_prob = (precedent_prob * 0.75) + (forum_weight * 100 * 0.25)

        # 3. Factor in specific facts and arguments
        facts_lower = litigation.facts_summary.lower()
        company_args_lower = litigation.company_arguments.lower()

        # Specific checks for Section 14A
        if "14a" in " ".join(litigation.sections).lower():
            if "reserves" in facts_lower or "interest-free" in company_args_lower or "surplus" in company_args_lower:
                calculated_prob -= 12.0
                mitigating_factors.append("Company demonstrates owned surplus interest-free funds exceed investments (South Indian Bank presumption applies).")
            if "nil exempt income" in company_args_lower or "no dividend" in company_args_lower:
                calculated_prob -= 15.0
                mitigating_factors.append("Argument of nil/low exempt income earned during the year supported by Cheminvest HC ruling.")

        # Specific checks for Section 36(1)(va) employee PF
        if "36(1)(va)" in " ".join(litigation.sections).lower() or "pf" in facts_lower:
            calculated_prob = max(calculated_prob, 95.0)
            risk_drivers.append("Supreme Court in Checkmate Services (2022) established non-negotiable strict liability against late employee PF deposits.")

        # Specific checks for GST ITC Section 16(2)(c)
        if "16(2)(c)" in " ".join(litigation.sections).lower():
            if "e-way" in company_args_lower or "bank" in company_args_lower or "suncraft" in company_args_lower:
                calculated_prob -= 15.0
                mitigating_factors.append("Bona fide recipient defence supported by Calcutta HC Suncraft Energy & Madras HC D.Y. Beathel precedents.")
            if "cancelled retrospectively" in facts_lower or "fake invoice" in facts_lower:
                calculated_prob += 20.0
                risk_drivers.append("Supplier GSTIN cancelled retrospectively or tagged under fake invoice / non-existent entity list.")

        # Specific checks for Transfer Pricing AMP
        if "92c" in " ".join(litigation.sections).lower() or "amp" in facts_lower:
            if "bright line" in litigation.department_arguments.lower():
                calculated_prob -= 18.0
                mitigating_factors.append("Department relied on Bright Line Test which has been repeatedly struck down by Delhi HC (Sony Ericsson / Maruti Suzuki).")

        # Bound probability between 1% and 99%
        calculated_prob = round(max(1.0, min(99.0, calculated_prob)), 1)

        # 4. Map to Ind AS 37 / AS 29 Standard
        if calculated_prob > 50.0:
            classification = IndAS37Status.PROBABLE
            risk_drivers.append("Probability exceeds 50%: Outflow of economic benefits is PROBABLE under Ind AS 37.")
        elif calculated_prob >= 10.0:
            classification = IndAS37Status.POSSIBLE
            mitigating_factors.append("Probability within 10%-50%: Classified as POSSIBLE contingent liability (disclosure required in notes to accounts).")
        else:
            classification = IndAS37Status.REMOTE
            mitigating_factors.append("Probability below 10%: Classified as REMOTE risk under Ind AS 37.")

        # 5. Formulate M&A Due Diligence Deal Recommendations
        deal_rec = cls._create_deal_recommendation(
            prob=calculated_prob,
            classification=classification,
            exposure=exposure,
            litigation=litigation
        )

        return AssessmentResult(
            litigation=litigation,
            crystallization_probability=calculated_prob,
            ind_as_37_classification=classification,
            court_hierarchy_weight=court_hierarchy_wt,
            matching_precedents=matches,
            exposure=exposure,
            deal_recommendation=deal_rec,
            key_risk_drivers=risk_drivers,
            mitigating_factors=mitigating_factors
        )

    @classmethod
    def _create_deal_recommendation(
        cls,
        prob: float,
        classification: IndAS37Status,
        exposure: ExposureBreakdown,
        litigation: TaxLitigation
    ) -> DealRecommendation:
        total_exp = exposure.total_gross_exposure
        base_demand = exposure.base_tax_demand

        if classification == IndAS37Status.PROBABLE:
            ebitda_adj = True
            # Recommend dollar-for-dollar net debt deduction on Base + Accrued Interest
            net_debt_deduction = exposure.base_tax_demand + exposure.interest_amount
            escrow = total_exp
            memo = (
                f"HIGH DEAL IMPACT: Materialization is PROBABLE ({prob}%). Target company should have provided "
                f"for this under Ind AS 37 / AS 29. Recommend reducing purchase consideration via EV-to-Equity Net Debt "
                f"adjustment of INR {net_debt_deduction:,.0f} (Base Demand + Accrued Interest). Demand 100% promoter specific "
                f"indemnity without de minimis or basket thresholds."
            )
        elif classification == IndAS37Status.POSSIBLE:
            ebitda_adj = False
            net_debt_deduction = 0.0
            # Sizing escrow holdback: typically expected value or 50%-100% of demand
            escrow = round(total_exp * (prob / 100.0), 2)
            memo = (
                f"MODERATE DEAL IMPACT: Materialization is POSSIBLE ({prob}%). Full P&L provision not mandatory under "
                f"Ind AS 37, but buyer is exposed to crystallization upon adverse appellate ruling. Recommend a Specific Tax "
                f"Indemnity backed by an Escrow Holdback of INR {escrow:,.0f} (or bank guarantee) expiring 12 months after "
                f"final tribunal disposal."
            )
        else:
            ebitda_adj = False
            net_debt_deduction = 0.0
            escrow = 0.0
            memo = (
                f"LOW DEAL IMPACT: Materialization is REMOTE ({prob}%). Precedents strongly favor the company. "
                f"Standard fundamental tax representations and general tax indemnity basket are sufficient; no escrow holdback "
                f"or purchase price deduction warranted."
            )

        return DealRecommendation(
            accounting_treatment=classification,
            ebitda_adjustment_recommended=ebitda_adj,
            net_debt_deduction_amount=net_debt_deduction,
            specific_indemnity_needed=(classification != IndAS37Status.REMOTE),
            escrow_holdback_suggested=escrow,
            deal_negotiation_memo=memo
        )
