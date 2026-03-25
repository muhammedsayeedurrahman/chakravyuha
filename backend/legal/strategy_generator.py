"""Strategy Generator - Create action plans and next steps for legal cases."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import json
from pathlib import Path


class CourtType(Enum):
    """Types of courts."""
    POLICE_STATION = "Police Station"  # For FIR
    DISTRICT_COURT = "District Court"  # Civil/Criminal trial
    HIGH_COURT = "High Court"  # Appeals
    SUPREME_COURT = "Supreme Court"  # Constitutional matters


@dataclass
class ActionStep:
    """Action step in legal strategy."""
    step_number: int
    title: str
    description: str
    timeline: str  # e.g., "Within 7 days"
    estimated_cost: Optional[str] = None
    responsible_party: str = "Advocate/Client"


@dataclass
class StrategyPlan:
    """Complete action plan for case."""
    case_type: str
    recommended_forum: CourtType
    total_timeline: str
    total_estimated_cost: str
    steps: List[ActionStep] = field(default_factory=list)
    evidence_checklist: List[str] = field(default_factory=list)
    cost_breakdown: Dict[str, str] = field(default_factory=dict)
    mediation_recommended: bool = False
    next_immediate_action: str = ""


class StrategyGenerator:
    """Generate action plans and strategy for legal cases."""
    
    def __init__(self):
        """Initialize strategy generator with rules."""
        self.strategy_rules = self._load_strategy_rules()
    
    def _load_strategy_rules(self) -> dict:
        """Load strategy rules from data."""
        return {
            "Theft": {
                "forum": "DISTRICT_COURT",
                "timeline": "2-3 years",
                "cost": "₹50,000 - ₹150,000",
                "evidence": ["FIR copy", "Police report", "Stolen item value proof", "Receipts"],
                "steps": [
                    {"title": "File FIR", "timeline": "Immediately", "cost": "Free"},
                    {"title": "Collect evidence", "timeline": "Within 15 days", "cost": "FIR copy: ₹200"},
                    {"title": "Lodge complaint", "timeline": "Within 60 days", "cost": "₹100"},
                    {"title": "Lawyer consultation", "timeline": "Before filing", "cost": "₹2,000-5,000"},
                ],
                "mediation": False,
            },
            "Murder": {
                "forum": "DISTRICT_COURT",
                "timeline": "3-5 years",
                "cost": "₹150,000 - ₹500,000+",
                "evidence": ["Post-mortem report", "Eye witnesses", "Weapon", "Motive evidence"],
                "steps": [
                    {"title": "File FIR", "timeline": "Immediately", "cost": "Free"},
                    {"title": "Crime scene investigation", "timeline": "10-15 days", "cost": "Conducted by police"},
                    {"title": "Medical post-mortem", "timeline": "Within 24 hours", "cost": "Free (by police)"},
                    {"title": "Engage lawyer", "timeline": "Before arrest", "cost": "₹5,000-20,000"},
                    {"title": "Court proceedings begin", "timeline": "After investigation", "cost": "Court fees: ₹1,000+"},
                ],
                "mediation": False,
            },
            "Hurt": {
                "forum": "DISTRICT_COURT",
                "timeline": "1-2 years",
                "cost": "₹30,000 - ₹100,000",
                "evidence": ["Medical certificate", "Photographs", "Witnesses"],
                "steps": [
                    {"title": "Get medical examination", "timeline": "Within 24 hours", "cost": "₹500-1,000"},
                    {"title": "File FIR", "timeline": "Within 7 days", "cost": "Free"},
                    {"title": "Collect witness statements", "timeline": "Within 15 days", "cost": "FIR copy: ₹200"},
                    {"title": "Lawyer consultation", "timeline": "Before filing", "cost": "₹1,500-3,000"},
                ],
                "mediation": True,
            },
            "Cheating": {
                "forum": "DISTRICT_COURT",
                "timeline": "2-3 years",
                "cost": "₹40,000 - ₹150,000",
                "evidence": ["Documents/proof", "Bank statements", "Communication records"],
                "steps": [
                    {"title": "Gather documentation", "timeline": "ASAP", "cost": "Document copies: ₹500"},
                    {"title": "Complaint to police", "timeline": "Within 30 days", "cost": "Free"},
                    {"title": "File FIR", "timeline": "After complaint", "cost": "Free"},
                    {"title": "Legal consultation", "timeline": "Before court filing", "cost": "₹2,000-5,000"},
                ],
                "mediation": True,
            },
        }
    
    def generate_strategy(self, case_type: str, offense_sections: List[str]) -> StrategyPlan:
        """
        Generate comprehensive legal strategy.
        
        Args:
            case_type: Type of case (Murder, Theft, Hurt, Cheating)
            offense_sections: Applicable BNS sections
            
        Returns:
            Complete action plan
        """
        rules = self.strategy_rules.get(case_type, self._default_strategy())
        
        # Create action steps
        steps = []
        for i, step_data in enumerate(rules.get("steps", []), 1):
            steps.append(
                ActionStep(
                    step_number=i,
                    title=step_data.get("title", ""),
                    description=f"Required step: {step_data.get('title', '')}",
                    timeline=step_data.get("timeline", "TBD"),
                    estimated_cost=step_data.get("cost", "Varies"),
                )
            )
        
        # Build cost breakdown
        cost_breakdown = {
            "FIR filing": "Free",
            "Police charges": "Varies",
            "Advocate fees": "₹2,000-5,000 (initial consultation)",
            "Court fees": "₹1,000+",
            "Document copies": "₹200-500",
            "Medical/expert reports": "₹500-5,000",
            "Investigation costs": "Generally by police",
        }
        
        # Determine forum
        forum_map = {
            "DISTRICT_COURT": CourtType.DISTRICT_COURT,
            "HIGH_COURT": CourtType.HIGH_COURT,
            "POLICE_STATION": CourtType.POLICE_STATION,
        }
        forum = forum_map.get(rules.get("forum", "DISTRICT_COURT"), CourtType.DISTRICT_COURT)
        
        return StrategyPlan(
            case_type=case_type,
            recommended_forum=forum,
            total_timeline=rules.get("timeline", "2-3 years"),
            total_estimated_cost=rules.get("cost", "₹50,000 - ₹150,000"),
            steps=steps,
            evidence_checklist=rules.get("evidence", []),
            cost_breakdown=cost_breakdown,
            mediation_recommended=rules.get("mediation", False),
            next_immediate_action=steps[0].title if steps else "Consult with advocate immediately",
        )
    
    @staticmethod
    def _default_strategy() -> dict:
        """Default strategy for unknown case type."""
        return {
            "forum": "DISTRICT_COURT",
            "timeline": "2-3 years",
            "cost": "₹50,000 - ₹150,000",
            "evidence": ["Documents", "Witnesses", "Physical evidence"],
            "steps": [
                {"title": "Consult with advocate", "timeline": "Immediately", "cost": "₹2,000-5,000"},
                {"title": "Gather evidence", "timeline": "Within 15 days", "cost": "Varies"},
                {"title": "File complaint/FIR", "timeline": "Within 60 days", "cost": "₹100-500"},
                {"title": "Court proceedings", "timeline": "2-3 years", "cost": "Court fees"},
            ],
            "mediation": False,
        }
