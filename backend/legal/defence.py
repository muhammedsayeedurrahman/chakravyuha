"""Defence strategy generation per legal section."""

import json
from pathlib import Path
from backend.config import DATA_DIR


class DefenceAdvisor:
    """Provides defence strategies and step-by-step guidance for legal sections."""

    def __init__(self):
        path = DATA_DIR / "defence_strategies.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._strategies = {s["section_id"]: s for s in data["strategies"]}

    def get_defence_strategy(self, section_id: str) -> dict | None:
        """Get defence strategies for a given BNS section.

        Args:
            section_id: e.g. 'BNS-100'

        Returns:
            Dict with scenario and list of defences, or None if not found.
        """
        return self._strategies.get(section_id)

    def get_step_by_step_guidance(self, section_id: str, language: str = "en") -> list[str]:
        """Get plain-language step-by-step guidance for a section.

        Args:
            section_id: BNS section ID.
            language: 'en' for English, 'hi' for Hindi.

        Returns:
            List of step strings.
        """
        strategy = self._strategies.get(section_id)
        if not strategy:
            if language == "hi":
                return ["इस धारा के लिए विस्तृत मार्गदर्शन उपलब्ध नहीं है। कृपया वकील से संपर्क करें।"]
            return ["Detailed guidance not available for this section. Please consult a lawyer."]

        defences = strategy.get("defences", [])
        if language == "hi":
            steps = [f"आप पर {strategy['scenario']} का आरोप है। संभावित बचाव:"]
            for i, d in enumerate(defences, 1):
                steps.append(f"{i}. {d['name']}: {d['description']}")
            steps.append("कृपया किसी योग्य वकील से परामर्श लें।")
        else:
            steps = [f"You are accused of: {strategy['scenario']}. Possible defences:"]
            for i, d in enumerate(defences, 1):
                steps.append(f"{i}. {d['name']}: {d['description']}")
                steps.append(f"   Applicable when: {d['applicability']}")
            steps.append("Please consult a qualified lawyer for personalized legal advice.")

        return steps

    def list_available_sections(self) -> list[str]:
        """Return list of section IDs that have defence strategies."""
        return list(self._strategies.keys())
