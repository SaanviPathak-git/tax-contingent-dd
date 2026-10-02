"""
Tax Exposure and Financial Risk Quantification Engine.
Calculates Base Tax, Statutory Interest (Direct Tax Sec 234A/B/C/220 vs GST Sec 50),
Penalty Ranges (Sec 270A/271(1)(c) vs GST Sec 73/74), and Appeal Stay Deposits.
"""

from datetime import datetime, date
from typing import Dict, Any, Optional
from core.models import TaxLitigation, ExposureBreakdown

class ExposureCalculator:
    """Calculates granular financial liabilities and cash flow drag for corporate tax disputes."""

    @staticmethod
    def calculate_direct_tax_exposure(
        base_demand: float,
        notice_date_str: str,
        evaluation_date: Optional[date] = None,
        assessment_year: str = "AY 2020-21",
        allegation_severity: str = "underreporting"  # 'underreporting' (50%), 'misreporting' (200%), or 'bonafide' (0%)
    ) -> ExposureBreakdown:
        if evaluation_date is None:
            evaluation_date = date.today()

        try:
            notice_date = datetime.strptime(notice_date_str, "%Y-%m-%d").date()
        except Exception:
            notice_date = date(2022, 3, 31)

        # Parse AY to determine start of Sec 234B interest (1st April of AY)
        try:
            # Format usually "AY 2020-21" -> 2020
            ay_start_year = int(assessment_year.replace("AY", "").strip().split("-")[0])
            sec_234b_start = date(ay_start_year, 4, 1)
        except Exception:
            sec_234b_start = date(2020, 4, 1)

        # Section 234B Interest: 1% per month or part of month from April 1 of AY to notice date
        months_234b = max(1, (notice_date.year - sec_234b_start.year) * 12 + (notice_date.month - sec_234b_start.month))
        # Standard cap/rate: 1% per month
        interest_234b = base_demand * 0.01 * months_234b

        # Section 234C Interest: Deferment of advance tax installments (typically ~3.5% of demand)
        interest_234c = base_demand * 0.035

        # Section 220(2) Interest: 1% per month from 30 days after notice date till evaluation date
        days_since_notice = (evaluation_date - notice_date).days
        months_220_2 = max(0, (days_since_notice - 30) // 30)
        interest_220_2 = base_demand * 0.01 * months_220_2

        total_interest = interest_234b + interest_234c + interest_220_2

        # Penalty Assessment u/s 270A
        if allegation_severity == "misreporting":
            penalty_min = base_demand * 0.50
            penalty_max = base_demand * 2.00
            penalty_recommended = base_demand * 2.00
        elif allegation_severity == "underreporting":
            penalty_min = base_demand * 0.50
            penalty_max = base_demand * 0.50
            penalty_recommended = base_demand * 0.50
        else:  # bona fide dispute / debatable legal issue
            penalty_min = 0.0
            penalty_max = base_demand * 0.50
            penalty_recommended = base_demand * 0.25

        total_gross = base_demand + total_interest + penalty_recommended
        stay_deposit_needed = base_demand * 0.20  # 20% CBDT mandate for stay before CIT(A) / ITAT

        return ExposureBreakdown(
            base_tax_demand=base_demand,
            interest_amount=total_interest,
            interest_breakdown={
                "Interest u/s 234B (Advance Tax Default)": round(interest_234b, 2),
                "Interest u/s 234C (Advance Tax Deferment)": round(interest_234c, 2),
                "Interest u/s 220(2) (Post-Demand Delay)": round(interest_220_2, 2)
            },
            penalty_estimated_min=penalty_min,
            penalty_estimated_max=penalty_max,
            penalty_recommended=penalty_recommended,
            total_gross_exposure=round(total_gross, 2),
            pre_deposit_paid=0.0,
            remaining_cash_at_risk=round(total_gross, 2),
            appeal_stay_deposit_needed=round(stay_deposit_needed, 2)
        )

    @staticmethod
    def calculate_gst_exposure(
        base_demand: float,
        notice_date_str: str,
        evaluation_date: Optional[date] = None,
        is_fraud_or_suppression: bool = False
    ) -> ExposureBreakdown:
        if evaluation_date is None:
            evaluation_date = date.today()

        try:
            notice_date = datetime.strptime(notice_date_str, "%Y-%m-%d").date()
        except Exception:
            notice_date = date(2023, 4, 1)

        # Statutory Interest u/s 50(1) @ 18% p.a. from notice / due date
        days_elapsed = max(30, (evaluation_date - notice_date).days + 365)  # include period from return due date
        years_elapsed = days_elapsed / 365.25
        interest_50 = base_demand * 0.18 * years_elapsed

        # Penalty Assessment
        if is_fraud_or_suppression:
            # Section 74: 100% of tax
            penalty_min = base_demand * 0.50
            penalty_max = base_demand * 1.00
            penalty_recommended = base_demand * 1.00
            penalty_type = "Section 74 (Fraud / Willful Misstatement 100%)"
        else:
            # Section 73: 10% of tax or 10,000
            penalty_min = max(10000.0, base_demand * 0.10)
            penalty_max = max(10000.0, base_demand * 0.10)
            penalty_recommended = penalty_max
            penalty_type = "Section 73 (Non-Fraud 10%)"

        total_gross = base_demand + interest_50 + penalty_recommended
        appeal_pre_deposit = min(250000000.0, base_demand * 0.10)  # 10% under Section 107

        return ExposureBreakdown(
            base_tax_demand=base_demand,
            interest_amount=round(interest_50, 2),
            interest_breakdown={
                "Statutory Interest u/s 50(1) (18% p.a.)": round(interest_50, 2)
            },
            penalty_estimated_min=round(penalty_min, 2),
            penalty_estimated_max=round(penalty_max, 2),
            penalty_recommended=round(penalty_recommended, 2),
            total_gross_exposure=round(total_gross, 2),
            pre_deposit_paid=0.0,
            remaining_cash_at_risk=round(total_gross, 2),
            appeal_stay_deposit_needed=round(appeal_pre_deposit, 2)
        )

    @classmethod
    def evaluate_litigation(cls, litigation: TaxLitigation) -> ExposureBreakdown:
        is_gst = "GST" in litigation.tax_type or "Indirect" in litigation.tax_type
        if is_gst:
            is_fraud = "74" in " ".join(litigation.sections) or "suppression" in litigation.department_arguments.lower()
            exposure = cls.calculate_gst_exposure(
                base_demand=litigation.disputed_base_demand,
                notice_date_str=litigation.demand_notice_date,
                is_fraud_or_suppression=is_fraud
            )
        else:
            allegation = "misreporting" if "270A(8)" in litigation.department_arguments or "misreporting" in litigation.department_arguments.lower() else "underreporting"
            exposure = cls.calculate_direct_tax_exposure(
                base_demand=litigation.disputed_base_demand,
                notice_date_str=litigation.demand_notice_date,
                assessment_year=litigation.assessment_year,
                allegation_severity=allegation
            )

        exposure.pre_deposit_paid = litigation.pre_deposit_paid
        exposure.remaining_cash_at_risk = max(0.0, exposure.total_gross_exposure - litigation.pre_deposit_paid)
        return exposure
