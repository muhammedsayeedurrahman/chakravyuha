"""Focused regression tests for guided-flow service and civic handoffs."""

import pytest

from backend.legal.guided_flow import GuidedFlow
from backend.agent.orchestrator import Orchestrator
from backend.models.schemas import GuidedFlowState
from backend.services.legal_service import LegalService


@pytest.fixture
def flow() -> GuidedFlow:
    return GuidedFlow()


@pytest.fixture
def service() -> LegalService:
    return LegalService()


def test_legacy_root_alias_resolves_to_start(flow: GuidedFlow) -> None:
    result = flow.get_current_question({"current_node": "root"})

    assert result["node_id"] == "start"
    assert result["question"] == "What happened to you?"


def test_existing_criminal_option_positions_are_preserved(flow: GuidedFlow) -> None:
    labels = [option["label"] for option in flow.get_current_question(flow.reset())["options"]]

    assert labels[:8] == [
        "Accident / Vehicle Issue",
        "Theft / Robbery",
        "Assault / Violence",
        "Family / Domestic Issue",
        "Fraud / Cheating",
        "Sexual Offence",
        "Property Dispute",
        "Threat / Intimidation",
    ]
    assert labels[-1] == "Other"


@pytest.mark.parametrize(
    ("label", "journey", "handler"),
    [
        ("RTI / Public Records", "rti", "rti_assistant"),
        ("Government Scheme Eligibility", "scheme_eligibility", "scheme_eligibility"),
        ("Consumer Dispute", "consumer", "civic_legal_query"),
        ("Tenant / Landlord Issue", "tenant", "civic_legal_query"),
        ("Workplace / Labour Issue", "labour", "civic_legal_query"),
        ("Government Grievance (CPGRAMS)", "cpgrams", "cpgrams_assistant"),
    ],
)
def test_civic_options_use_nonterminal_handoffs(
    flow: GuidedFlow, label: str, journey: str, handler: str
) -> None:
    initial = flow.get_current_question(flow.reset())
    index = next(i for i, option in enumerate(initial["options"]) if option["label"] == label)

    result = flow.process_answer(flow.reset(), index)

    assert result["terminal"] is False
    assert result["type"] == "handoff"
    assert result["journey"] == journey
    assert result["handler"] == handler
    assert result["prompt"]
    assert result["next_steps"]


def test_service_accepts_legacy_root_state(service: LegalService) -> None:
    legacy = service.get_guided_step(GuidedFlowState(current_node="root"))
    current = service.get_guided_step(GuidedFlowState(current_node="start"))

    assert legacy.node_key == "start"
    assert legacy.question == current.question
    assert [option.label for option in legacy.options] == [
        option.label for option in current.options
    ]


def test_service_resolves_node_level_terminal(service: LegalService) -> None:
    theft_branch = service.process_guided_answer(
        GuidedFlowState(current_node="start"), "Theft / Robbery"
    )
    terminal = service.process_guided_answer(
        GuidedFlowState(current_node=theft_branch.node_key),
        "Something was stolen (no violence)",
    )

    assert theft_branch.node_key == "theft_branch"
    assert terminal.node_key == "theft_simple"
    assert terminal.is_leaf is True
    assert terminal.summary == "Theft - dishonest taking of property"
    assert terminal.next_steps
    assert {section.section_id for section in terminal.matched_sections} >= {
        "BNS-305",
        "IPC-378",
    }


def test_service_exposes_handoff_metadata(service: LegalService) -> None:
    result = service.process_guided_answer(
        GuidedFlowState(current_node="root"), "RTI / Public Records"
    )

    assert result.is_leaf is False
    assert result.type == "handoff"
    assert result.journey == "rti"
    assert result.handler == "rti_assistant"
    assert result.prompt == result.question
    assert result.next_steps


def test_agent_guided_adapter_preserves_handoff_metadata() -> None:
    orchestrator = object.__new__(Orchestrator)
    orchestrator._guided_flow = GuidedFlow()
    initial = orchestrator._guided_flow.get_current_question(
        orchestrator._guided_flow.reset()
    )
    option_index = next(
        index
        for index, option in enumerate(initial["options"])
        if option["label"] == "Government Scheme Eligibility"
    )

    result = orchestrator.process_guided_answer(option_index, {})

    assert result["type"] == "handoff"
    assert result["journey"] == "scheme_eligibility"
    assert result["handler"] == "scheme_eligibility"
    assert result["next_steps"]
