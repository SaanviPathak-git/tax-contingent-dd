"""
Streamlit Web Dashboard for Tax Due Diligence & Contingent Liability Assessment.
Designed for Chartered Accountants, M&A Tax Advisors, and Litigation Specialists.
"""

import streamlit as st
import json
from pathlib import Path
from datetime import date
import pandas as pd

from core.models import TaxLitigation, PrecedentCase, IndAS37Status
from core.exposure_calculator import ExposureCalculator
from core.precedent_engine import PrecedentEngine
from core.hierarchy_scorer import HierarchyScorer
from core.report_generator import ReportGenerator

st.set_page_config(
    page_title="Tax Due Diligence & Contingent Liability Evaluator",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for executive aesthetic
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1E3A8A; margin-bottom: 0.2rem; }
    .sub-header { font-size: 1.05rem; color: #4B5563; margin-bottom: 1.5rem; }
    .card { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 20px; margin-bottom: 15px; }
    .metric-value { font-size: 1.8rem; font-weight: 700; }
    .metric-label { font-size: 0.85rem; color: #64748B; text-transform: uppercase; font-weight: 600; }
    .badge-probable { background-color: #FEE2E2; color: #991B1B; padding: 4px 10px; border-radius: 9999px; font-weight: 600; font-size: 0.85rem; }
    .badge-possible { background-color: #FEF3C7; color: #92400E; padding: 4px 10px; border-radius: 9999px; font-weight: 600; font-size: 0.85rem; }
    .badge-remote { background-color: #DCFCE7; color: #166534; padding: 4px 10px; border-radius: 9999px; font-weight: 600; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

# Helper function to load samples
@st.cache_data
def load_sample_cases():
    data_path = Path(__file__).parent / "data" / "sample_litigations.json"
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)

sample_cases = load_sample_cases()

# Sidebar: Case Selection & Inputs
st.sidebar.image("https://img.icons8.com/color/96/scales--v1.png", width=64)
st.sidebar.title("Tax DD Navigator")
st.sidebar.caption("Chartered Accountant & M&A Diligence Engine")

case_mode = st.sidebar.radio(
    "Dispute Input Mode:",
    ["Benchmark Corporate Cases", "Custom Case Intake / SCN Upload"]
)

if case_mode == "Benchmark Corporate Cases":
    case_names = [f"{c['company_name']} - {c['dispute_type']}" for c in sample_cases]
    selected_idx = st.sidebar.selectbox("Select Target Company Case:", range(len(case_names)), format_func=lambda i: case_names[i])
    current_case_dict = sample_cases[selected_idx]
    
    company_name = current_case_dict["company_name"]
    ay = current_case_dict["assessment_year"]
    tax_type = current_case_dict["tax_type"]
    dispute_type = current_case_dict["dispute_type"]
    sections = current_case_dict["sections"]
    forum = current_case_dict["forum"]
    state = current_case_dict["jurisdiction_state"]
    base_demand = float(current_case_dict["disputed_base_demand"])
    notice_date = current_case_dict["demand_notice_date"]
    facts = current_case_dict["facts_summary"]
    dept_args = current_case_dict["department_arguments"]
    company_args = current_case_dict["company_arguments"]
    pre_deposit_paid = current_case_dict.get("pre_deposit_paid", 0.0)
    status_str = current_case_dict["status"]
else:
    st.sidebar.subheader("New Litigation Ingestion")
    company_name = st.sidebar.text_input("Target Entity Name:", "Target Pharma India Ltd")
    tax_type = st.sidebar.selectbox("Tax Domain:", ["Direct Tax", "Indirect Tax (GST)"])
    dispute_type = st.sidebar.text_input("Dispute Subject:", "Disallowance u/s 14A / Section 16(2)(c)")
    ay = st.sidebar.text_input("Assessment Year / Period:", "AY 2021-22")
    sections_str = st.sidebar.text_input("Sections Involved (comma separated):", "Section 14A, Rule 8D")
    sections = [s.strip() for s in sections_str.split(",") if s.strip()]
    forum = st.sidebar.selectbox(
        "Current Appellate Forum:",
        [
            "Assessing Officer (AO / Faceless AO)",
            "Dispute Resolution Panel (DRP) / CIT(A)",
            "Income Tax Appellate Tribunal (ITAT)",
            "Adjudicating Authority (GST)",
            "GST Appellate Authority (Joint Commissioner Appeals)",
            "GST Appellate Tribunal (GSTAT)",
            "High Court",
            "Supreme Court of India"
        ]
    )
    state = st.sidebar.selectbox("Jurisdiction State:", ["Maharashtra", "Delhi", "Karnataka", "West Bengal", "Tamil Nadu", "Gujarat", "Other"])
    base_demand = st.sidebar.number_input("Disputed Base Demand (INR):", min_value=10000.0, value=25000000.0, step=500000.0)
    notice_date = st.sidebar.date_input("Date of SCN / Demand Notice:", date(2022, 10, 15)).strftime("%Y-%m-%d")
    pre_deposit_paid = st.sidebar.number_input("Pre-deposit Paid Under Protest (INR):", min_value=0.0, value=5000000.0, step=100000.0)
    facts = st.sidebar.text_area("Factual Matrix & Core Dispute:", "Assessing Officer disallowed interest expense alleging deployment of borrowed funds into exempt dividend yielding equities.")
    dept_args = st.sidebar.text_area("Tax Department's Contention:", "Rule 8D formula is mandatory. Mixed pool of borrowed funds used for investments.")
    company_args = st.sidebar.text_area("Assessee's Contention & Defences:", "Own interest-free funds exceed tax-free investments. South Indian Bank precedent applies.")
    status_str = "Appeal pending before ITAT."

# Build litigation object
litigation = TaxLitigation(
    id="ACTIVE-001",
    company_name=company_name,
    assessment_year=ay,
    tax_type=tax_type,
    dispute_type=dispute_type,
    sections=sections,
    forum=forum,
    jurisdiction_state=state,
    disputed_base_demand=base_demand,
    demand_notice_date=notice_date,
    facts_summary=facts,
    department_arguments=dept_args,
    company_arguments=company_args,
    status=status_str,
    pre_deposit_paid=pre_deposit_paid
)

# Run Engines
precedent_engine = PrecedentEngine()
matches = precedent_engine.find_relevant_precedents(litigation)
exposure = ExposureCalculator.evaluate_litigation(litigation)
result = HierarchyScorer.evaluate_probability(litigation, matches, exposure)

# Header
st.markdown('<div class="main-header">⚖️ Tax Due Diligence & Contingent Liability Evaluator</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Evaluating probability of contingent liabilities crystallizing into actual liabilities under '
    '<strong>Ind AS 37 / AS 29</strong> using <strong>Supreme Court & High Court Precedent RAG</strong>.</div>',
    unsafe_allow_html=True
)

# Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Diligence Assessment & Ind AS 37",
    "⚖️ Judicial Precedents & Ratio Decidendi",
    "💰 Exposure & Interest Waterfall",
    "📝 Executive DD Memo & Export"
])

with tab1:
    col1, col2, col3, col4 = st.columns(4)
    
    # Probability badge color
    prob = result.crystallization_probability
    if prob > 50:
        badge_html = f'<span class="badge-probable">PROBABLE ({prob}%)</span>'
    elif prob >= 10:
        badge_html = f'<span class="badge-possible">POSSIBLE ({prob}%)</span>'
    else:
        badge_html = f'<span class="badge-remote">REMOTE ({prob}%)</span>'

    with col1:
        st.markdown(f"""
        <div class="card">
            <div class="metric-label">Crystallization Risk</div>
            <div class="metric-value">{prob}%</div>
            <div>{badge_html}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="card">
            <div class="metric-label">Disputed Base Tax</div>
            <div class="metric-value">₹ {exposure.base_tax_demand/1e7:.2f} Cr</div>
            <div style="font-size: 0.85rem; color:#64748B;">{litigation.assessment_year} | {litigation.forum}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="card">
            <div class="metric-label">Total Gross Exposure</div>
            <div class="metric-value" style="color: #DC2626;">₹ {exposure.total_gross_exposure/1e7:.2f} Cr</div>
            <div style="font-size: 0.85rem; color:#64748B;">Tax + Accrued Int + Penalty</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="card">
            <div class="metric-label">M&A Purchase Price Drag</div>
            <div class="metric-value" style="color: #D97706;">₹ {result.deal_recommendation.net_debt_deduction_amount/1e7:.2f} Cr</div>
            <div style="font-size: 0.85rem; color:#64748B;">EV-to-Equity Net Debt Cut</div>
        </div>
        """, unsafe_allow_html=True)

    # Ind AS 37 Accounting Matrix Callout
    st.markdown("### 📋 Accounting Standard & M&A Deal Guidance")
    deal = result.deal_recommendation
    if result.ind_as_37_classification == IndAS37Status.PROBABLE:
        st.error(f"⚠️ **Ind AS 37 Classification: {result.ind_as_37_classification.value}**\n\n{deal.deal_negotiation_memo}")
    elif result.ind_as_37_classification == IndAS37Status.POSSIBLE:
        st.warning(f"🔔 **Ind AS 37 Classification: {result.ind_as_37_classification.value}**\n\n{deal.deal_negotiation_memo}")
    else:
        st.success(f"✅ **Ind AS 37 Classification: {result.ind_as_37_classification.value}**\n\n{deal.deal_negotiation_memo}")

    # Risk Drivers and Mitigating Factors
    col_risk, col_mit = st.columns(2)
    with col_risk:
        st.markdown("#### 🚨 Key Risk Aggravators")
        for r in result.key_risk_drivers:
            st.markdown(f"- ❌ {r}")
    with col_mit:
        st.markdown("#### 🛡️ Defense & Mitigating Factors")
        for m in result.mitigating_factors:
            st.markdown(f"- ✔️ {m}")

    st.markdown("---")
    st.markdown("#### 📈 Probability & Ind AS 37 Scale")
    st.progress(prob / 100.0)
    col_p1, col_p2, col_p3 = st.columns([1, 4, 5])
    col_p1.caption("0% - 10%: Remote (No Note)")
    col_p2.caption("10% - 50%: Possible (Contingent Liability Note)")
    col_p3.caption("50% - 100%: Probable (Mandatory Balance Sheet Provision)")

with tab2:
    st.markdown("### ⚖️ Landmark Precedent Mapping & Ratio Decidendi")
    st.markdown(
        f"Evaluating judicial precedents for **{litigation.dispute_type}** across the **Indian Judicial Hierarchy** "
        f"(Supreme Court Article 141 binding law vs Jurisdictional High Court in {litigation.jurisdiction_state})."
    )

    if not matches:
        st.info("No direct landmark cases retrieved for this query. The assessment is running on judicial forum baselines.")
    else:
        for idx, match in enumerate(matches, 1):
            p = match.precedent
            is_sc = "Supreme Court" in match.binding_authority
            card_border = "#2563EB" if is_sc else "#94A3B8"
            favorable_color = "#15803D" if p.favorable_to == "Assessee" else "#B91C1C"

            with st.expander(f"#{idx}. {p.case_title} — [{p.citation}] | {match.binding_authority}", expanded=(idx==1)):
                col_c1, col_c2, col_c3 = st.columns([2, 1, 1])
                col_c1.markdown(f"**Forum / Court:** {p.court} ({p.year})")
                col_c2.markdown(f"**Favorable To:** <span style='color:{favorable_color}; font-weight:bold;'>{p.favorable_to}</span>", unsafe_allow_html=True)
                col_c3.markdown(f"**Relevance Match:** `{match.relevance_score * 100:.0f}%`")

                st.markdown(f"**Dispute Subject:** {p.subject}")
                
                col_arg1, col_arg2 = st.columns(2)
                with col_arg1:
                    st.markdown("**🏛️ Department's Position:**")
                    st.info(p.department_position)
                with col_arg2:
                    st.markdown("**🏢 Assessee's Stance:**")
                    st.success(p.assessee_position)

                st.markdown("**📜 Ratio Decidendi (Binding Legal Principle):**")
                st.markdown(f"> *{p.ratio_decidendi}*")

                st.markdown("**🔍 Distinguishing Factors (Check Target Company's Facts):**")
                for f_item in p.key_distinguishing_factors:
                    st.markdown(f"- 📌 {f_item}")

with tab3:
    st.markdown("### 💰 Financial Exposure & Cash Flow Waterfall")
    st.markdown(
        "Direct Tax statutory interest accumulates under Sections 234A/B/C and Section 220(2). "
        "GST interest accumulates under Section 50(1) at **18% p.a.** Penalties and statutory pre-deposits create substantial cash drag."
    )

    col_exp_table, col_exp_summary = st.columns([3, 2])

    with col_exp_table:
        exposure_data = [
            {"Component": "1. Disputed Base Tax Demand", "Amount (INR)": f"₹ {exposure.base_tax_demand:,.2f}", "Remarks": f"Disputed under {', '.join(litigation.sections)}"},
            {"Component": "2. Accrued Statutory Interest", "Amount (INR)": f"₹ {exposure.interest_amount:,.2f}", "Remarks": "Calculated up to assessment date"},
            {"Component": "3. Potential Penalties (Est. Range)", "Amount (INR)": f"₹ {exposure.penalty_recommended:,.2f}", "Remarks": f"Min: ₹{exposure.penalty_estimated_min:,.0f} | Max: ₹{exposure.penalty_estimated_max:,.0f}"},
            {"Component": "TOTAL GROSS EXPOSURE", "Amount (INR)": f"₹ {exposure.total_gross_exposure:,.2f}", "Remarks": "Total financial claim by Revenue"},
            {"Component": "Less: Pre-deposit Paid Under Protest", "Amount (INR)": f"- ₹ {exposure.pre_deposit_paid:,.2f}", "Remarks": "Already deposited with treasury"},
            {"Component": "NET UNFUNDED CASH AT RISK", "Amount (INR)": f"₹ {exposure.remaining_cash_at_risk:,.2f}", "Remarks": "Outstanding exposure to buyer"}
        ]
        df_exposure = pd.DataFrame(exposure_data)
        st.dataframe(df_exposure, use_container_width=True, hide_index=True)

        st.markdown("#### Granular Interest Breakdown")
        for item, amt in exposure.interest_breakdown.items():
            st.markdown(f"- **{item}:** `₹ {amt:,.2f}`")

    with col_exp_summary:
        st.markdown(f"""
        <div class="card">
            <h4>Appeal Stay / Cash Outflow Alert</h4>
            <p>Under CBDT Directives / GST Act provisions:</p>
            <ul>
                <li><strong>Statutory Pre-deposit Needed:</strong> ₹ {exposure.appeal_stay_deposit_needed:,.2f}</li>
                <li><strong>Pre-deposit Already Paid:</strong> ₹ {exposure.pre_deposit_paid:,.2f}</li>
                <li><strong>Immediate Cash Drain for Stay:</strong> ₹ {max(0.0, exposure.appeal_stay_deposit_needed - exposure.pre_deposit_paid):,.2f}</li>
            </ul>
            <div style="font-size: 0.85rem; color: #64748B;">
                CBDT OM requires 20% deposit for stay before ITAT/CIT(A). Section 107 of CGST Act mandates 10% pre-deposit for appeal admission.
            </div>
        </div>
        """, unsafe_allow_html=True)

with tab4:
    st.markdown("### 📝 Boardroom Tax Due Diligence Memo")
    st.markdown("Generate and download the executive-ready Tax Due Diligence Memo for M&A deal teams, CFOs, and Investment Committees.")

    report_md = ReportGenerator.generate_markdown_report(result)
    report_html = ReportGenerator.generate_html_report(result)

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        st.download_button(
            label="📥 Download Diligence Memo (Markdown)",
            data=report_md,
            file_name=f"Tax_DD_Memo_{litigation.company_name.replace(' ', '_')}.md",
            mime="text/markdown",
            use_container_width=True
        )
    with col_btn2:
        st.download_button(
            label="🌐 Download Diligence Memo (Printable HTML / PDF Ready)",
            data=report_html,
            file_name=f"Tax_DD_Memo_{litigation.company_name.replace(' ', '_')}.html",
            mime="text/html",
            use_container_width=True
        )

    st.markdown("---")
    st.markdown("#### Document Preview")
    st.markdown(report_md)
