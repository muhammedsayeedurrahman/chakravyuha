"""BNS/IPC section lookup and cross-reference mapping."""

import json
from pathlib import Path
from backend.config import DATA_DIR


class SectionLookup:
    """Load and query BNS/IPC sections with cross-reference mapping."""

    def __init__(self):
        self._bns = self._load_json(DATA_DIR / "bns_sections.json")["sections"]
        self._ipc = self._load_json(DATA_DIR / "ipc_sections.json")["sections"]
        mapping_data = self._load_json(DATA_DIR / "ipc_to_bns_mapping.json")
        self._ipc_to_bns = {m["ipc"]: m["bns"] for m in mapping_data["mappings"]}
        self._bns_to_ipc = {m["bns"]: m["ipc"] for m in mapping_data["mappings"]}

        # Index by section_id for O(1) lookup
        self._bns_index = {s["section_id"]: s for s in self._bns}
        self._ipc_index = {s["section_id"]: s for s in self._ipc}

    @staticmethod
    def _load_json(path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def lookup_section(self, section_id: str) -> dict | None:
        """Look up full details for a BNS or IPC section.

        Args:
            section_id: e.g. 'BNS-100' or 'IPC-302'

        Returns:
            Section dict or None if not found.
        """
        if section_id.startswith("BNS"):
            return self._bns_index.get(section_id)
        if section_id.startswith("IPC"):
            return self._ipc_index.get(section_id)
        return None

    def search_sections(self, keyword: str, law: str = "both") -> list[dict]:
        """Search sections by keyword in title, description, and keywords list.

        Args:
            keyword: Search term (case-insensitive).
            law: 'bns', 'ipc', or 'both'.

        Returns:
            List of matching section dicts with a 'match_score' field.
        """
        keyword_lower = keyword.lower()
        results = []
        sources = []
        if law in ("bns", "both"):
            sources.extend(self._bns)
        if law in ("ipc", "both"):
            sources.extend(self._ipc)

        for section in sources:
            score = 0
            if keyword_lower in section.get("title", "").lower():
                score += 3
            if keyword_lower in section.get("description", "").lower():
                score += 2
            if any(keyword_lower in kw.lower() for kw in section.get("keywords", [])):
                score += 4
            if score > 0:
                results.append({**section, "match_score": score})

        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results

    def ipc_to_bns(self, ipc_section: str) -> str | None:
        """Get the BNS equivalent of an IPC section."""
        return self._ipc_to_bns.get(ipc_section)

    def bns_to_ipc(self, bns_section: str) -> str | None:
        """Get the IPC equivalent of a BNS section."""
        return self._bns_to_ipc.get(bns_section)

    def get_both_laws(self, section_id: str) -> dict:
        """Get section details from both BNS and IPC for cross-reference.

        Args:
            section_id: Any section ID (BNS or IPC).

        Returns:
            Dict with 'bns' and 'ipc' keys, each containing section details or None.
        """
        if section_id.startswith("BNS"):
            bns_data = self.lookup_section(section_id)
            ipc_id = self.bns_to_ipc(section_id)
            ipc_data = self.lookup_section(ipc_id) if ipc_id else None
        elif section_id.startswith("IPC"):
            ipc_data = self.lookup_section(section_id)
            bns_id = self.ipc_to_bns(section_id)
            bns_data = self.lookup_section(bns_id) if bns_id else None
        else:
            return {"bns": None, "ipc": None}

        return {"bns": bns_data, "ipc": ipc_data}
