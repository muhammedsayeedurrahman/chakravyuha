"""Data loader — load legal sections, mappings, guided tree, and defence strategies from JSON."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from backend.config import DATA_DIR
from backend.models.schemas import LegalSection

logger = logging.getLogger("chakravyuha")


def _load_json(filename: str) -> dict | list:
    """Load a JSON file from the data directory."""
    path = Path(DATA_DIR) / filename
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_section_index() -> dict[str, LegalSection]:
    """Build a section_id -> LegalSection index from BNS and IPC JSON files."""
    index: dict[str, LegalSection] = {}

    # Load BNS sections
    try:
        bns_data = _load_json("bns_sections.json")
        for entry in bns_data.get("sections", []):
            section = LegalSection(
                section_id=entry["section_id"],
                title=entry.get("title", ""),
                act="BNS 2023",
                chapter=entry.get("chapter", ""),
                description=entry.get("description", ""),
                punishment=entry.get("punishment", ""),
                cognizable=entry.get("cognizable", False),
                bailable=entry.get("bailable", True),
                court=entry.get("court", ""),
                replaces_ipc=entry.get("replaces_ipc"),
                keywords=entry.get("keywords", []),
            )
            index[section.section_id] = section
    except Exception as e:
        logger.warning("Failed to load BNS sections: %s", e)

    # Load IPC sections
    try:
        ipc_data = _load_json("ipc_sections.json")
        for entry in ipc_data.get("sections", []):
            section = LegalSection(
                section_id=entry["section_id"],
                title=entry.get("title", ""),
                act="IPC 1860",
                chapter=entry.get("chapter", ""),
                description=entry.get("description", ""),
                punishment=entry.get("punishment", ""),
                cognizable=entry.get("cognizable", False),
                bailable=entry.get("bailable", True),
                court=entry.get("court", ""),
                replaced_by_bns=entry.get("bns_equivalent"),
                keywords=entry.get("keywords", []),
            )
            index[section.section_id] = section
    except Exception as e:
        logger.warning("Failed to load IPC sections: %s", e)

    logger.debug("Section index built: %d sections", len(index))
    return index


def build_keyword_index(section_index: dict[str, "LegalSection"] | None = None) -> dict[str, list[str]]:
    """Build a keyword -> list[section_id] reverse index."""
    keyword_index: dict[str, list[str]] = {}
    if section_index is None:
        section_index = build_section_index()

    for sid, section in section_index.items():
        for kw in section.keywords:
            kw_lower = kw.lower()
            if kw_lower not in keyword_index:
                keyword_index[kw_lower] = []
            if sid not in keyword_index[kw_lower]:
                keyword_index[kw_lower].append(sid)

    logger.debug("Keyword index built: %d keywords", len(keyword_index))
    return keyword_index


def load_guided_tree() -> dict:
    """Load the guided flow decision tree."""
    try:
        return _load_json("guided_flow_tree.json")
    except Exception as e:
        logger.warning("Failed to load guided flow tree: %s", e)
        return {}


def load_defence_strategies() -> list[dict]:
    """Load defence strategies data."""
    try:
        data = _load_json("defence_strategies.json")
        return data.get("strategies", [])
    except Exception as e:
        logger.warning("Failed to load defence strategies: %s", e)
        return []


def load_ipc_to_bns_map() -> dict[str, str]:
    """Load IPC -> BNS section mapping."""
    try:
        data = _load_json("ipc_to_bns_mapping.json")
        mapping: dict[str, str] = {}
        for entry in data.get("mappings", []):
            mapping[entry["ipc"]] = entry["bns"]
        return mapping
    except Exception as e:
        logger.warning("Failed to load IPC->BNS mapping: %s", e)
        return {}


def load_bns_to_ipc_map() -> dict[str, str]:
    """Load BNS -> IPC section mapping (reverse of ipc_to_bns)."""
    try:
        data = _load_json("ipc_to_bns_mapping.json")
        mapping: dict[str, str] = {}
        for entry in data.get("mappings", []):
            mapping[entry["bns"]] = entry["ipc"]
        return mapping
    except Exception as e:
        logger.warning("Failed to load BNS->IPC mapping: %s", e)
        return {}
