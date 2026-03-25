"""
Nyaya Entity Extractor - Extract legal concepts from Indian language queries

Entities:
- STATUTE: IPC, BNS, CrPC, etc.
- SECTION: Section 302, Article 15
- OFFENSE: murder, theft, hurt
- PUNISHMENT: imprisonment, fine
- JURISDICTION: magistrate, sessions court
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List
import json
import os
import re


class EntityType(Enum):
    """Types of legal entities that can be extracted"""
    STATUTE = "STATUTE"
    SECTION = "SECTION"
    OFFENSE = "OFFENSE"
    PUNISHMENT = "PUNISHMENT"
    JURISDICTION = "JURISDICTION"


@dataclass
class NyayaEntity:
    """Represents a legal entity extracted from text"""
    text: str
    entity_type: EntityType
    statute_reference: str  # e.g., "IPC-302" or "BNS-103"
    confidence: float
    alternate_names: List[str] = field(default_factory=list)


class NyayaEntityExtractor:
    """Extract legal entities from user queries in Indian languages"""

    def __init__(self):
        """Load IPC↔BNS mapping and initialize pattern dictionaries"""
        self.mappings = self._load_ipc_bns_mapping()

        # Common offense keywords in English and Hindi
        self.offense_keywords = {
            "hurt": {
                "ipc": "IPC-323",
                "bns": "BNS-115",
                "hindi": ["चोट", "मारना", "पीटना"],
                "confidence": 0.85
            },
            "murder": {
                "ipc": "IPC-302",
                "bns": "BNS-103",
                "hindi": ["हत्या", "मार डाला", "वध"],
                "confidence": 0.95
            },
            "theft": {
                "ipc": "IPC-379",
                "bns": "BNS-303",
                "hindi": ["चोरी", "चुरा लिया"],
                "confidence": 0.90
            },
            "rape": {
                "ipc": "IPC-376",
                "bns": "BNS-64",
                "hindi": ["बलात्कार"],
                "confidence": 0.95
            },
            "cheating": {
                "ipc": "IPC-420",
                "bns": "BNS-318",
                "hindi": ["धोखाधड़ी", "ठगी"],
                "confidence": 0.85
            },
            "cruelty": {
                "ipc": "IPC-498A",
                "bns": "BNS-85",
                "hindi": ["क्रूरता", "प्रताड़ना"],
                "confidence": 0.80
            },
        }

        # Jurisdiction keywords
        self.jurisdiction_keywords = {
            "magistrate": {"code": "MM", "level": "lower"},
            "sessions": {"code": "SESSIONS", "level": "upper"},
            "high court": {"code": "HC", "level": "appellate"},
            "supreme court": {"code": "SC", "level": "final"},
        }

    def _load_ipc_bns_mapping(self) -> dict:
        """Load IPC↔BNS mapping from JSON file"""
        mapping_file = os.path.join(
            os.path.dirname(__file__), "../../data/ipc_bns_mapping.json"
        )
        try:
            with open(mapping_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("sections", {})
        except FileNotFoundError:
            print(f"⚠️  Warning: {mapping_file} not found. Using empty mapping.")
            return {}

    def extract(self, text: str, language: str = "hi") -> List[NyayaEntity]:
        """
        Extract legal entities from user query text
        
        Args:
            text: User query in English or regional language
            language: Language code (hi, ta, te, kn, ml, etc.)
        
        Returns:
            List of extracted legal entities with confidence scores
        """
        entities = []

        # Convert to lowercase for matching
        text_lower = text.lower()

        # Extract offenses from keywords
        for offense, info in self.offense_keywords.items():
            if offense in text_lower:
                # Check for Hindi variants too
                for hindi_variant in info.get("hindi", []):
                    if hindi_variant in text:
                        break
                
                entities.append(
                    NyayaEntity(
                        text=offense,
                        entity_type=EntityType.OFFENSE,
                        statute_reference=info["bns"],  # Prefer BNS (newer)
                        confidence=info.get("confidence", 0.85),
                        alternate_names=info.get("hindi", []),
                    )
                )
                break  # Only add once per offense type

        # Extract sections (e.g., "section 302", "dhara 302", "खंड 302")
        section_pattern = r"(?:section|dhara|खंड|सेक्शन)\s*(\d+)"
        matches = re.finditer(section_pattern, text_lower, re.IGNORECASE)

        for match in matches:
            section_num = match.group(1)
            ipc_code = f"IPC-{section_num}"

            if ipc_code in self.mappings:
                mapping = self.mappings[ipc_code]
                bns_code = mapping.get("bns_code", ipc_code)

                entities.append(
                    NyayaEntity(
                        text=f"Section {section_num}",
                        entity_type=EntityType.SECTION,
                        statute_reference=bns_code,
                        confidence=0.95,
                        alternate_names=[ipc_code],
                    )
                )

        # Extract jurisdiction information
        for jurisdiction, info in self.jurisdiction_keywords.items():
            if jurisdiction in text_lower:
                entities.append(
                    NyayaEntity(
                        text=jurisdiction,
                        entity_type=EntityType.JURISDICTION,
                        statute_reference=info["code"],
                        confidence=0.80,
                    )
                )

        return entities

    def get_statute_details(self, ipc_code: str) -> dict:
        """Get detailed information for a statute code"""
        if ipc_code in self.mappings:
            mapping = self.mappings[ipc_code]
            return {
                "ipc_code": ipc_code,
                "bns_code": mapping.get("bns_code"),
                "title": mapping.get("title"),
                "punishment": mapping.get("punishment"),
                "type": mapping.get("type"),
                "cognizable": mapping.get("cognizable", False),
                "bailable": mapping.get("bailable", True),
            }
        return {"error": f"{ipc_code} not found"}


# Example usage and testing
if __name__ == "__main__":
    extractor = NyayaEntityExtractor()

    # Test queries
    test_queries = [
        "Mere sath marof hua",  # Hurt in Hindi
        "Section 302 under IPC",  # Murder section
        "Ye theft case magistrate court mein hai",  # Theft + jurisdiction
        "बलात्कार का मामला",  # Rape in Hindi
    ]

    print("🧪 Testing Nyaya Entity Extractor:\n")
    for query in test_queries:
        print(f"Query: {query}")
        entities = extractor.extract(query)
        if entities:
            for entity in entities:
                print(
                    f"  ✓ {entity.text} ({entity.entity_type.value}) → {entity.statute_reference} (conf: {entity.confidence:.2f})"
                )
        else:
            print("  ✗ No entities extracted")
        print()
