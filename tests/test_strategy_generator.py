"""Tests for Strategy Generator."""

import pytest
from backend.legal.strategy_generator import StrategyGenerator, CourtType


@pytest.fixture
def generator():
    return StrategyGenerator()


def test_generate_strategy_theft(generator):
    """Test strategy generation for theft case."""
    strategy = generator.generate_strategy(
        case_type="Theft",
        offense_sections=["BNS-303"],
    )
    
    assert strategy.case_type == "Theft"
    assert strategy.recommended_forum == CourtType.DISTRICT_COURT
    assert len(strategy.steps) > 0
    assert "₹" in strategy.total_estimated_cost


def test_generate_strategy_murder(generator):
    """Test strategy generation for murder case."""
    strategy = generator.generate_strategy(
        case_type="Murder",
        offense_sections=["BNS-103"],
    )
    
    assert strategy.case_type == "Murder"
    assert len(strategy.steps) > 0


def test_strategy_includes_evidence_checklist(generator):
    """Verify strategy includes evidence checklist."""
    strategy = generator.generate_strategy(
        case_type="Hurt",
        offense_sections=["BNS-115"],
    )
    
    assert len(strategy.evidence_checklist) > 0


def test_strategy_includes_cost_breakdown(generator):
    """Verify strategy includes cost breakdown."""
    strategy = generator.generate_strategy(
        case_type="Cheating",
        offense_sections=["BNS-317"],
    )
    
    assert len(strategy.cost_breakdown) > 0


def test_strategy_timeline_format(generator):
    """Verify strategy timeline is in correct format."""
    strategy = generator.generate_strategy(
        case_type="Theft",
        offense_sections=["BNS-303"],
    )
    
    # Should contain year/month/day info
    assert "year" in strategy.total_timeline.lower() or "day" in strategy.total_timeline.lower()


def test_strategy_immediate_action(generator):
    """Verify strategy has immediate next action."""
    strategy = generator.generate_strategy(
        case_type="Murder",
        offense_sections=["BNS-103"],
    )
    
    assert len(strategy.next_immediate_action) > 0


def test_all_steps_have_details(generator):
    """Verify all action steps have required fields."""
    strategy = generator.generate_strategy(
        case_type="Hurt",
        offense_sections=["BNS-115"],
    )
    
    for step in strategy.steps:
        assert step.step_number > 0
        assert len(step.title) > 0
        assert len(step.timeline) > 0
