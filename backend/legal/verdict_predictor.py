"""AI Judge - Verdict Prediction Engine."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum
import json
from pathlib import Path


class VerdictType(Enum):
    """Predicted verdict types."""
    GUILTY = "GUILTY"
    NOT_GUILTY = "NOT_GUILTY"
    PARTIALLY_GUILTY = "PARTIALLY_GUILTY"
    ACQUITTAL = "ACQUITTAL"
    CONVICTION = "CONVICTION"


@dataclass
class EvidenceScore:
    """Score for each piece of evidence."""
    evidence: str
    relevance_score: float  # 0.0 - 1.0
    strength: str  # Strong, Moderate, Weak
    impact: str  # "Increases conviction likelihood" or "Decreases"


@dataclass
class VerdictPrediction:
    """Verdict prediction result."""
    predicted_verdict: VerdictType
    confidence: float  # 0.0 - 1.0
    responsible_section: str  # BNS code
    outcome_description: str
    likelihood_percentage: int
    evidence_scores: List[EvidenceScore] = field(default_factory=list)
    reasoning: List[str] = field(default_factory=list)
    similar_cases: List[str] = field(default_factory=list)


class VerdictPredictor:
    """Predict verdict based on case facts."""
    
    def __init__(self):
        """Initialize verdict predictor with case precedents and rules."""
        self.precedents = self._load_precedents()
        self.section_rules = self._load_section_rules()
    
    def _load_precedents(self) -> dict:
        """Load case precedents from JSON."""
        precedent_file = Path(__file__).parent.parent.parent / "data" / "case_precedents.json"
        try:
            with open(precedent_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"cases": self._default_precedents()}
    
    def _load_section_rules(self) -> dict:
        """Load BNS section rules for verdict prediction."""
        return {
            "BNS-103": {  # Murder
                "min_evidence": 2,
                "evidence_keywords": ["weapon", "witness", "motive", "premeditation"],
                "base_conviction_rate": 0.75,
                "punishment": "Death or life imprisonment",
            },
            "BNS-115": {  # Hurt
                "min_evidence": 1,
                "evidence_keywords": ["injury", "medical certificate", "witness"],
                "base_conviction_rate": 0.65,
                "punishment": "6 months imprisonment or fine",
            },
            "BNS-303": {  # Theft
                "min_evidence": 1,
                "evidence_keywords": ["stolen item", "CCTV", "witness", "possession"],
                "base_conviction_rate": 0.58,
                "punishment": "7 years imprisonment",
            },
            "BNS-350": {  # Criminal intimidation
                "min_evidence": 1,
                "evidence_keywords": ["threat", "witness", "written message"],
                "base_conviction_rate": 0.62,
                "punishment": "3 years imprisonment or fine",
            },
            "BNS-356": {  # Wrongful restraint
                "min_evidence": 1,
                "evidence_keywords": ["witness", "medical", "location"],
                "base_conviction_rate": 0.60,
                "punishment": "3 months imprisonment or fine",
            },
        }
    
    def predict_verdict(
        self,
        case_type: str,
        offense_sections: List[str],
        description: str,
        evidence: List[str],
        witnesses: List[str],
    ) -> VerdictPrediction:
        """
        Predict verdict based on case details.
        
        Args:
            case_type: Type of case (e.g., "Murder", "Theft")
            offense_sections: Applicable BNS sections
            description: Case narrative
            evidence: Collected evidence
            witnesses: Number/names of witnesses
            
        Returns:
            VerdictPrediction with verdict, confidence, and reasoning
        """
        # Use primary offense section for prediction
        section = offense_sections[0] if offense_sections else "BNS-103"
        
        rules = self.section_rules.get(section, self._default_section_rule())
        
        # Calculate evidence score
        evidence_scores = self._score_evidence(evidence, section)
        total_evidence_strength = sum(e.relevance_score for e in evidence_scores) / max(len(evidence_scores), 1)
        
        # Calculate witness impact
        witness_count = len(witnesses)
        witness_boost = min(witness_count * 0.1, 0.3)  # Max 30% boost
        
        # Check minimum evidence requirement
        min_evidence_met = len(evidence) >= rules.get("min_evidence", 1)
        
        # Calculate base conviction probability
        base_rate = rules.get("base_conviction_rate", 0.60)
        
        # Start conviction calculation
        conviction_prob = base_rate
        
        if min_evidence_met:
            conviction_prob += (total_evidence_strength * 0.15)
        else:
            # If minimum evidence not met, significantly reduce confidence
            conviction_prob = conviction_prob * 0.4 - 0.2
        
        conviction_prob += witness_boost
        conviction_prob = min(max(conviction_prob, 0.0), 1.0)  # Clamp to [0, 1]
        
        # Determine verdict
        verdict = self._determine_verdict(conviction_prob, case_type)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            case_type,
            section,
            evidence_scores,
            witness_count,
            conviction_prob,
        )
        
        # Find similar cases
        similar = self._find_similar_cases(case_type, section)
        
        return VerdictPrediction(
            predicted_verdict=verdict,
            confidence=conviction_prob,
            responsible_section=section,
            outcome_description=f"{verdict.value} with {conviction_prob * 100:.0f}% likelihood",
            likelihood_percentage=int(conviction_prob * 100),
            evidence_scores=evidence_scores,
            reasoning=reasoning,
            similar_cases=similar,
        )
    
    def _score_evidence(self, evidence: List[str], section: str) -> List[EvidenceScore]:
        """Score each piece of evidence."""
        scores = []
        rules = self.section_rules.get(section, {})
        keywords = rules.get("evidence_keywords", [])
        
        for e in evidence:
            e_lower = e.lower()
            
            # Check keyword matches (more sensitive matching)
            matching_keywords = sum(1 for kw in keywords if kw.lower() in e_lower)
            
            # Calculate relevance with boosted scoring
            if matching_keywords >= 2:
                relevance = 0.9  # Very strong match
            elif matching_keywords == 1:
                relevance = 0.75  # Strong match
            else:
                # Check for partial matches
                partial_matches = sum(1 for kw in keywords if kw.lower()[:3] in e_lower)
                if partial_matches > 0:
                    relevance = 0.55  # Moderate match
                else:
                    relevance = 0.35  # Weak/generic evidence
            
            # Determine strength
            if relevance >= 0.8:
                strength = "Strong"
                impact = "Significantly increases conviction likelihood"
            elif relevance >= 0.5:
                strength = "Moderate"
                impact = "Moderately increases conviction likelihood"
            else:
                strength = "Weak"
                impact = "Slightly increases conviction likelihood"
            
            scores.append(
                EvidenceScore(
                    evidence=e,
                    relevance_score=relevance,
                    strength=strength,
                    impact=impact,
                )
            )
        
        return scores
    
    def _determine_verdict(self, conviction_prob: float, case_type: str) -> VerdictType:
        """Determine verdict based on conviction probability."""
        if conviction_prob >= 0.8:
            return VerdictType.CONVICTION
        elif conviction_prob >= 0.6:
            return VerdictType.PARTIALLY_GUILTY
        elif conviction_prob >= 0.4:
            return VerdictType.NOT_GUILTY
        else:
            return VerdictType.ACQUITTAL
    
    def _generate_reasoning(
        self,
        case_type: str,
        section: str,
        evidence_scores: List[EvidenceScore],
        witness_count: int,
        conviction_prob: float,
    ) -> List[str]:
        """Generate explanation for verdict."""
        reasoning = []
        
        reasoning.append(f"Based on case type '{case_type}' and section {section}:")
        
        if evidence_scores:
            strong_evidence = [e for e in evidence_scores if e.strength == "Strong"]
            reasoning.append(f"• Strength of evidence: {len(strong_evidence)} strong pieces")
        
        if witness_count > 0:
            reasoning.append(f"• Witness count: {witness_count} witness(es)")
        
        reasoning.append(f"• Overall conviction likelihood: {conviction_prob * 100:.0f}%")
        
        if conviction_prob >= 0.8:
            reasoning.append("• Status: Strong case for prosecution")
        elif conviction_prob >= 0.6:
            reasoning.append("• Status: Moderate case for prosecution")
        else:
            reasoning.append("• Status: Weak case for prosecution")
        
        return reasoning
    
    def _find_similar_cases(self, case_type: str, section: str) -> List[str]:
        """Find similar precedent cases."""
        similar = []
        
        for case in self.precedents.get("cases", []):
            if case.get("type") == case_type or case.get("section") == section:
                similar.append(f"{case.get('name', 'Unknown')} ({case.get('year', '2023')})")
        
        return similar[:3]  # Return top 3
    
    @staticmethod
    def _default_section_rule() -> dict:
        """Default rule for unknown section."""
        return {
            "min_evidence": 1,
            "evidence_keywords": ["witness", "evidence"],
            "base_conviction_rate": 0.50,
            "punishment": "As per law",
        }
    
    @staticmethod
    def _default_precedents() -> List[dict]:
        """Default precedent cases."""
        return [
            {
                "name": "Sharma v. State",
                "type": "Murder",
                "section": "BNS-103",
                "year": 2023,
                "verdict": "Guilty",
            },
            {
                "name": "Kumar v. State",
                "type": "Theft",
                "section": "BNS-303",
                "year": 2024,
                "verdict": "Guilty",
            },
            {
                "name": "Patel v. State",
                "type": "Hurt",
                "section": "BNS-115",
                "year": 2023,
                "verdict": "Guilty",
            },
            {
                "name": "Singh v. State",
                "type": "Criminal intimidation",
                "section": "BNS-350",
                "year": 2024,
                "verdict": "Not Guilty",
            },
        ]
