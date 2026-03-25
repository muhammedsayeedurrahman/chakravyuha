"""Tests for guided question flow → section mapping."""

import pytest
from backend.legal.guided_flow import GuidedFlow


@pytest.fixture
def flow():
    return GuidedFlow()


class TestGuidedFlow:
    def test_initial_question(self, flow):
        state = flow.reset()
        result = flow.get_current_question(state)
        assert result["node_id"] == "start"
        assert not result["terminal"]
        assert "question" in result
        assert len(result["options"]) >= 5

    def test_navigate_to_theft(self, flow):
        state = flow.reset()
        # Select "Theft / Robbery" (index 1)
        result = flow.process_answer(state, 1)
        assert "state" in result
        assert result["state"]["current_node"] == "theft_branch"
        assert not result.get("terminal", False)
        assert "options" in result

    def test_navigate_to_simple_theft_terminal(self, flow):
        state = flow.reset()
        # Select "Theft / Robbery" → "Something was stolen (no violence)"
        result = flow.process_answer(state, 1)
        state2 = result["state"]
        result2 = flow.process_answer(state2, 0)
        assert result2.get("terminal") is True
        assert "BNS-305" in result2.get("sections", [])

    def test_navigate_to_robbery(self, flow):
        state = flow.reset()
        result = flow.process_answer(state, 1)  # theft branch
        state2 = result["state"]
        result2 = flow.process_answer(state2, 2)  # robbery
        assert result2.get("terminal") is True
        assert "BNS-65" in result2.get("sections", [])
        assert result2.get("escalation") is True

    def test_navigate_to_accident_death(self, flow):
        state = flow.reset()
        result = flow.process_answer(state, 0)  # accident branch
        state2 = result["state"]
        result2 = flow.process_answer(state2, 0)  # someone died
        assert result2.get("terminal") is True
        assert "BNS-124" in result2.get("sections", [])

    def test_navigate_to_domestic_violence(self, flow):
        state = flow.reset()
        result = flow.process_answer(state, 3)  # family branch
        state2 = result["state"]
        result2 = flow.process_answer(state2, 0)  # domestic violence
        assert result2.get("terminal") is True
        assert "BNS-85" in result2.get("sections", [])
        assert result2.get("escalation") is True

    def test_navigate_to_fraud(self, flow):
        state = flow.reset()
        result = flow.process_answer(state, 4)  # fraud branch
        state2 = result["state"]
        result2 = flow.process_answer(state2, 0)  # cheating
        assert result2.get("terminal") is True
        assert "BNS-318" in result2.get("sections", [])

    def test_navigate_to_free_text(self, flow):
        state = flow.reset()
        # Select "Other" (last option)
        options = flow.get_current_question(state)["options"]
        last_index = len(options) - 1
        result = flow.process_answer(state, last_index)
        assert result.get("type") == "free_text"

    def test_invalid_option_index(self, flow):
        state = flow.reset()
        result = flow.process_answer(state, 99)
        assert "error" in result

    def test_history_tracking(self, flow):
        state = flow.reset()
        result = flow.process_answer(state, 0)
        assert "start" in result["state"]["history"]

    def test_sexual_offence_branch(self, flow):
        state = flow.reset()
        result = flow.process_answer(state, 5)  # sexual branch
        state2 = result["state"]
        result2 = flow.process_answer(state2, 4)  # rape
        assert result2.get("terminal") is True
        assert "BNS-63" in result2.get("sections", [])
        assert result2.get("escalation") is True

    def test_all_terminal_nodes_have_sections(self, flow):
        """Ensure every terminal node maps to at least one section."""
        import json
        from backend.config import DATA_DIR

        with open(DATA_DIR / "guided_flow_tree.json", "r", encoding="utf-8") as f:
            tree = json.load(f)

        for node_id, node in tree.items():
            if isinstance(node, dict) and node.get("terminal"):
                sections = node.get("sections", [])
                assert len(sections) > 0, f"Terminal node '{node_id}' has no sections"
