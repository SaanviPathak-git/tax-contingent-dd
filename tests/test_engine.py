"""
Unit and Integration Tests for Tax Due Diligence Engine.
Verifies Ind AS 37 compliance, precedent retrieval, exposure math, and report generation.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core.models import TaxLitigation, IndAS37Status
from core.exposure_calculator import ExposureCalculator
from core.precedent_engine import PrecedentEngine
from core.hierarchy_scorer import HierarchyScorer
from core.report_generator import ReportGenerator

def test_exposure_calculator():
    # Direct tax test
    dt_exp = ExposureCalculator.calculate_direct_tax_exposure(
        base_demand=10000000.0,
        notice_date_str="2022-03-31",
        assessment_year="AY 2020-21",
        allegation_severity="underreporting"
    )
    assert dt_exp.base_tax_demand == 10000000.0
    assert dt_exp.interest_amount > 0
    assert dt_exp.penalty_recommended == 5000000.0  # 50%
    assert dt_exp.appeal_stay_deposit_needed == 2000000.0  # 20%
    print("[PASS] Exposure calculator (Direct Tax) passed")

    # GST test
    gst_exp = ExposureCalculator.calculate_gst_exposure(
        base_demand=5000000.0,
        notice_date_str="2023-01-01",
        is_fraud_or_suppression=False
    )
    assert gst_exp.base_tax_demand == 5000000.0
    assert gst_exp.interest_amount > 0
    assert gst_exp.penalty_recommended == 500000.0  # 10%
    print("[PASS] Exposure calculator (GST) passed")

def test_precedent_retrieval_and_scoring():
    engine = PrecedentEngine()
    assert len(engine.precedents) > 0
    print(f"[PASS] Loaded {len(engine.precedents)} landmark precedents")

    # Test Section 14A litigation
    case_14a = TaxLitigation(
        id="T1",
        company_name="Test Pharma Ltd",
        assessment_year="AY 2020-21",
        tax_type="Direct Tax",
        dispute_type="Disallowance of expense u/s 14A",
        sections=["Section 14A", "Rule 8D"],
        forum="Income Tax Appellate Tribunal (ITAT)",
        jurisdiction_state="Maharashtra",
        disputed_base_demand=45000000.0,
        demand_notice_date="2022-03-28",
        facts_summary="Disallowance of interest under Rule 8D(2)(ii) where free reserves exceed investments.",
        department_arguments="Mixed treasury pool used for share investment.",
        company_arguments="Owned interest-free funds exceed investments as per South Indian Bank ruling.",
        status="Pending at ITAT"
    )
    matches = engine.find_relevant_precedents(case_14a)
    assert len(matches) > 0
    print(f"[PASS] Matched {len(matches)} precedents for Section 14A")

    exp = ExposureCalculator.evaluate_litigation(case_14a)
    result = HierarchyScorer.evaluate_probability(case_14a, matches, exp)
    
    # Since reserves exceed investment and South Indian Bank is SC precedent, probability should be < 50% (Possible or Remote)
    assert result.crystallization_probability < 50.0
    assert result.ind_as_37_classification == IndAS37Status.POSSIBLE
    print(f"[PASS] Ind AS 37 result for Sec 14A: {result.crystallization_probability}% -> {result.ind_as_37_classification.value}")

    # Test Checkmate PF case (should be > 90% probable)
    case_pf = TaxLitigation(
        id="T2",
        company_name="Test Staffing Ltd",
        assessment_year="AY 2021-22",
        tax_type="Direct Tax",
        dispute_type="Delayed deposit of employee PF",
        sections=["Section 36(1)(va)", "Section 43B"],
        forum="CIT(A)",
        jurisdiction_state="Karnataka",
        disputed_base_demand=15000000.0,
        demand_notice_date="2022-12-10",
        facts_summary="Employee contribution to PF deposited after due date under PF Act.",
        department_arguments="Checkmate Services SC ruling mandates disallowance.",
        company_arguments="Deposited before ITR filing.",
        status="Pending at CIT(A)"
    )
    matches_pf = engine.find_relevant_precedents(case_pf)
    exp_pf = ExposureCalculator.evaluate_litigation(case_pf)
    result_pf = HierarchyScorer.evaluate_probability(case_pf, matches_pf, exp_pf)
    assert result_pf.crystallization_probability > 85.0
    assert result_pf.ind_as_37_classification == IndAS37Status.PROBABLE
    print(f"[PASS] Ind AS 37 result for Employee PF: {result_pf.crystallization_probability}% -> {result_pf.ind_as_37_classification.value}")

    # Test report generation
    md_rep = ReportGenerator.generate_markdown_report(result)
    assert "TAX DUE DILIGENCE REPORT" in md_rep
    assert "M&A Negotiation & Deal Structuring Impact" in md_rep
    print("[PASS] Report generator passed")

if __name__ == "__main__":
    test_exposure_calculator()
    test_precedent_retrieval_and_scoring()
    print("\nALL SYSTEM TESTS PASSED SUCCESSFULLY! [100%]")
