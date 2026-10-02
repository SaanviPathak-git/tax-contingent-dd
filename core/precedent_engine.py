"""
Precedent Knowledge Retrieval and Legal Text Matching Engine.
Retrieves landmark judgments, compares department vs. company arguments,
and weights court hierarchy (Article 141 Supreme Court vs. Jurisdictional HC).
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from core.models import PrecedentCase, PrecedentMatch, TaxLitigation

class PrecedentEngine:
    def __init__(self, data_path: Optional[str] = None):
        if data_path is None:
            data_path = str(Path(__file__).parent.parent / "data" / "landmark_precedents.json")
        self.data_path = data_path
        self.precedents: List[PrecedentCase] = self._load_precedents()

    def _load_precedents(self) -> List[PrecedentCase]:
        path = Path(self.data_path)
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [PrecedentCase(**item) for item in data]

    def add_custom_precedent(self, precedent: PrecedentCase):
        self.precedents.append(precedent)

    def find_relevant_precedents(self, litigation: TaxLitigation) -> List[PrecedentMatch]:
        lit_sections = {s.lower().replace(" ", "") for s in litigation.sections}
        lit_text = f"{litigation.dispute_type} {litigation.facts_summary} {litigation.department_arguments} {litigation.company_arguments}".lower()
        lit_tokens = set(re.findall(r"\b\w{3,}\b", lit_text))

        matches: List[PrecedentMatch] = []

        for prec in self.precedents:
            # 1. Section overlap score
            prec_sections = {s.lower().replace(" ", "") for s in prec.sections}
            section_overlap = len(lit_sections.intersection(prec_sections))
            section_score = 1.0 if section_overlap > 0 else 0.0

            # 2. Text keyword & factual similarity
            prec_text = f"{prec.subject} {prec.ratio_decidendi} {prec.department_position} {prec.assessee_position}".lower()
            prec_tokens = set(re.findall(r"\b\w{3,}\b", prec_text))
            
            token_intersection = lit_tokens.intersection(prec_tokens)
            token_union = lit_tokens.union(prec_tokens)
            jaccard_score = len(token_intersection) / max(1, len(token_union))

            # Bonus for direct phrase/subject hits
            phrase_bonus = 0.0
            for sec in litigation.sections:
                if sec.lower() in prec_text:
                    phrase_bonus += 0.25
            if litigation.dispute_type.lower() in prec_text or prec.subject.lower() in lit_text:
                phrase_bonus += 0.35

            raw_relevance = (section_score * 0.50) + (jaccard_score * 2.0) + phrase_bonus
            relevance = min(1.0, max(0.05, raw_relevance))

            # Only consider relevant cases
            if relevance < 0.20:
                continue

            # 3. Judicial Hierarchy & Binding Nature
            binding_authority, hierarchy_weight = self._determine_authority(
                prec=prec,
                lit_state=litigation.jurisdiction_state,
                lit_forum=litigation.forum
            )

            # 4. Impact Assessment
            if prec.favorable_to == "Revenue":
                impact = "Adverse / Pro-Revenue"
                # If adverse and highly binding, high crystallization risk
                crystallization_contribution = prec.pro_revenue_score * hierarchy_weight
            else:
                impact = "Favorable to Assessee"
                # If favorable and highly binding, lowers crystallization risk
                crystallization_contribution = (1.0 - (1.0 - prec.pro_revenue_score) * hierarchy_weight)

            # 5. Distinguishability Risk
            distinguish_risk = "Low" if relevance > 0.65 else ("Medium" if relevance > 0.40 else "High")

            match = PrecedentMatch(
                precedent=prec,
                relevance_score=round(relevance, 3),
                binding_authority=binding_authority,
                distinguishing_risk=distinguish_risk,
                net_impact=impact,
                weighted_crystallization_score=round(crystallization_contribution, 3)
            )
            matches.append(match)

        # Sort by relevance and hierarchy
        matches.sort(key=lambda m: (m.relevance_score, m.weighted_crystallization_score), reverse=True)
        return matches

    def _determine_authority(self, prec: PrecedentCase, lit_state: str, lit_forum: str) -> (str, float):
        """
        Determines whether the precedent is binding under Article 141 (SC) or
        Jurisdictional High Court, or merely persuasive.
        """
        court_lower = prec.court.lower()
        level = prec.hierarchy_level

        if "supreme court" in court_lower or level == "Supreme Court":
            return "Binding Law of the Land (Article 141)", 1.00

        # High Court check
        if "high court" in court_lower:
            # Check if jurisdictional
            is_jurisdictional = False
            for state in prec.applicable_states:
                if state.lower() == lit_state.lower() or state.lower() in lit_state.lower():
                    is_jurisdictional = True
                    break
            # Common High Court state mapping
            if "bombay" in court_lower and lit_state.lower() in ["maharashtra", "goa"]:
                is_jurisdictional = True
            elif "delhi" in court_lower and lit_state.lower() in ["delhi", "nct"]:
                is_jurisdictional = True
            elif "calcutta" in court_lower and lit_state.lower() in ["west bengal", "wb"]:
                is_jurisdictional = True
            elif "madras" in court_lower and lit_state.lower() in ["tamil nadu"]:
                is_jurisdictional = True
            elif "karnataka" in court_lower and lit_state.lower() in ["karnataka"]:
                is_jurisdictional = True

            if is_jurisdictional:
                return f"Jurisdictionally Binding ({prec.court})", 0.85
            else:
                return f"Highly Persuasive Authority ({prec.court})", 0.60

        if "special bench" in court_lower or "special bench" in level.lower():
            return "Binding on ITAT/Tribunal Benches", 0.50

        return "Persuasive / Factual Guidance", 0.35
