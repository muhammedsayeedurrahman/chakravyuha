"""Guided question flow — walks users through a decision tree to identify legal sections."""

import json
from pathlib import Path
from backend.config import DATA_DIR


class GuidedFlow:
    """Button-based guided flow that maps user answers to BNS/IPC sections."""

    def __init__(self, tree_path: str | None = None):
        path = Path(tree_path) if tree_path else DATA_DIR / "guided_flow_tree.json"
        with open(path, "r", encoding="utf-8") as f:
            self._tree = json.load(f)

    def get_current_question(self, state: dict) -> dict:
        """Return the current question and options based on session state.

        Args:
            state: Session state dict. Must contain 'current_node' key,
                   defaults to 'start' if missing.

        Returns:
            dict with keys: node_id, question, options, terminal, sections (if terminal)
        """
        node_id = state.get("current_node", "start")
        node = self._tree.get(node_id)
        if node is None:
            return {"error": f"Unknown node: {node_id}"}

        if node.get("terminal"):
            return {
                "node_id": node_id,
                "terminal": True,
                "sections": node.get("sections", []),
                "ipc_sections": node.get("ipc_sections", []),
                "summary": node.get("summary", ""),
                "summary_hi": node.get("summary_hi", ""),
                "next_steps": node.get("next_steps", []),
                "escalation": node.get("escalation", False),
            }

        if node.get("type") == "free_text":
            return {
                "node_id": node_id,
                "terminal": False,
                "type": "free_text",
                "prompt": node.get("prompt", ""),
                "prompt_hi": node.get("prompt_hi", ""),
                "handler": node.get("handler", "rag_pipeline"),
            }

        return {
            "node_id": node_id,
            "terminal": False,
            "question": node.get("question", ""),
            "question_hi": node.get("question_hi", ""),
            "options": [
                {"label": opt["label"], "label_hi": opt.get("label_hi", opt["label"])}
                for opt in node.get("options", [])
            ],
        }

    def process_answer(self, state: dict, answer_index: int) -> dict:
        """Advance the decision tree based on the user's selected option.

        Args:
            state: Current session state dict.
            answer_index: Zero-based index of the selected option.

        Returns:
            Updated state dict with new 'current_node' and the next question/result.
        """
        node_id = state.get("current_node", "start")
        node = self._tree.get(node_id)
        if node is None:
            return {"error": f"Unknown node: {node_id}"}

        options = node.get("options", [])
        if answer_index < 0 or answer_index >= len(options):
            return {"error": f"Invalid option index: {answer_index}"}

        next_node = options[answer_index]["next"]
        new_state = {**state, "current_node": next_node, "history": state.get("history", []) + [node_id]}
        result = self.get_current_question(new_state)
        result["state"] = new_state
        return result

    def reset(self) -> dict:
        """Return a fresh state starting from the beginning."""
        return {"current_node": "start", "history": []}
