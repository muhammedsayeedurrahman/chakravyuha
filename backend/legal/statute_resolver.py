"""
Statute Resolver - Handle IPC vs BNS transition (July 1, 2024)

IPC: Indian Penal Code, 1860 (old law - deprecated)
BNS: Bharatiya Nyaya Sanhita, 2023 (new law - current)

Same offenses, different section numbers. This module resolves between them.
"""

import json
import os
from typing import Dict, Optional


class StatuteResolver:
    """Resolve and convert between IPC and BNS statute codes"""

    def __init__(self):
        """Initialize with IPC↔BNS mapping"""
        self.mappings = self._load_mappings()

    def _load_mappings(self) -> dict:
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

    def resolve_to_bns(self, ipc_code: str) -> Dict:
        """
        Convert IPC code to BNS equivalent
        
        Args:
            ipc_code: e.g., "IPC-302"
        
        Returns:
            Dictionary with IPC and BNS information
        
        Example:
            >>> resolver.resolve_to_bns("IPC-302")
            {
                "ipc": "IPC-302",
                "ipc_title": "Punishment for murder",
                "bns": "BNS-103",
                "bns_title": "Punishment for murder",
                "effective_date": "2024-07-01",
                "status": "Both versions refer to same offense"
            }
        """
        if ipc_code not in self.mappings:
            return {
                "error": f"{ipc_code} not found in mappings",
                "ipc": ipc_code,
                "status": "Not mapped"
            }

        mapping = self.mappings[ipc_code]
        bns_code = mapping.get("bns_code", "")

        return {
            "ipc": ipc_code,
            "ipc_title": mapping.get("title", ""),
            "bns": bns_code,
            "bns_title": mapping.get("title", ""),  # Same title for both
            "effective_date": "2024-07-01",
            "status": "Both versions refer to same offense. Use BNS for current cases.",
            "recommendation": f"Use {bns_code} (current law effective from July 1, 2024)"
        }

    def resolve_to_ipc(self, bns_code: str) -> Dict:
        """
        Convert BNS code to IPC equivalent (reverse mapping)
        
        Args:
            bns_code: e.g., "BNS-103"
        
        Returns:
            Dictionary with IPC and BNS information
        """
        # Find matching IPC code for this BNS code
        for ipc_code, mapping in self.mappings.items():
            if mapping.get("bns_code") == bns_code:
                return {
                    "bns": bns_code,
                    "bns_title": mapping.get("title", ""),
                    "ipc": ipc_code,
                    "ipc_title": mapping.get("title", ""),
                    "effective_date": "2024-07-01",
                    "status": "BNS replaced IPC from July 1, 2024",
                    "note": f"Historical reference: IPC {ipc_code} replaced by {bns_code}"
                }

        return {
            "error": f"{bns_code} not found in mappings",
            "bns": bns_code,
            "status": "Not mapped"
        }

    def get_punishment(self, statute_code: str) -> str:
        """
        Get punishment details for a statute
        
        Args:
            statute_code: Either IPC code (e.g., "IPC-302") or BNS code (e.g., "BNS-103")
        
        Returns:
            Punishment description string
        
        Example:
            >>> resolver.get_punishment("BNS-103")
            "Death or life imprisonment + fine"
        """
        punishment_text = ""

        if statute_code.startswith("BNS"):
            # Convert BNS back to IPC to find in mappings
            for ipc, bns_data in self.mappings.items():
                if bns_data.get("bns_code") == statute_code:
                    punishment_text = bns_data.get("punishment", "Unknown")
                    break
        elif statute_code.startswith("IPC"):
            # It's IPC already
            if statute_code in self.mappings:
                punishment_text = self.mappings[statute_code].get("punishment", "Unknown")

        if not punishment_text:
            punishment_text = "Punishment information not available"

        return punishment_text

    def get_statute_details(self, statute_code: str) -> Dict:
        """
        Get comprehensive details for any statute code
        
        Args:
            statute_code: IPC or BNS code
        
        Returns:
            Dictionary with all statute details
        """
        if statute_code.startswith("IPC"):
            return self._get_ipc_details(statute_code)
        elif statute_code.startswith("BNS"):
            return self._get_bns_details(statute_code)
        else:
            return {"error": f"Unknown statute format: {statute_code}"}

    def _get_ipc_details(self, ipc_code: str) -> Dict:
        """Get details for an IPC section"""
        if ipc_code not in self.mappings:
            return {"error": f"{ipc_code} not found"}

        mapping = self.mappings[ipc_code]
        bns_code = mapping.get("bns_code", "")

        return {
            "statute_code": ipc_code,
            "status": "Deprecated (replaced by BNS on 2024-07-01)",
            "current_equivalent": bns_code,
            "title": mapping.get("title", ""),
            "punishment": mapping.get("punishment", ""),
            "type": mapping.get("type", ""),
            "cognizable": mapping.get("cognizable", False),
            "bailable": mapping.get("bailable", True),
            "court_jurisdiction": mapping.get("court", ""),
            "hindi_name": mapping.get("hindi", ""),
        }

    def _get_bns_details(self, bns_code: str) -> Dict:
        """Get details for a BNS section"""
        # Find the IPC code that maps to this BNS
        for ipc_code, mapping in self.mappings.items():
            if mapping.get("bns_code") == bns_code:
                return {
                    "statute_code": bns_code,
                    "status": "Current (effective from 2024-07-01)",
                    "replaced_ipc": ipc_code,
                    "title": mapping.get("title", ""),
                    "punishment": mapping.get("punishment", ""),
                    "type": mapping.get("type", ""),
                    "cognizable": mapping.get("cognizable", False),
                    "bailable": mapping.get("bailable", True),
                    "court_jurisdiction": mapping.get("court", ""),
                    "hindi_name": mapping.get("hindi", ""),
                }

        return {"error": f"{bns_code} not found in mappings"}

    def is_cognizable(self, statute_code: str) -> bool:
        """Check if offense is cognizable (police can arrest without warrant)"""
        if statute_code.startswith("IPC"):
            if statute_code in self.mappings:
                return self.mappings[statute_code].get("cognizable", False)
        elif statute_code.startswith("BNS"):
            for ipc, mapping in self.mappings.items():
                if mapping.get("bns_code") == statute_code:
                    return mapping.get("cognizable", False)
        return False

    def is_bailable(self, statute_code: str) -> bool:
        """Check if offense is bailable"""
        if statute_code.startswith("IPC"):
            if statute_code in self.mappings:
                return self.mappings[statute_code].get("bailable", True)
        elif statute_code.startswith("BNS"):
            for ipc, mapping in self.mappings.items():
                if mapping.get("bns_code") == statute_code:
                    return mapping.get("bailable", True)
        return True

    def get_jurisdiction_court(self, statute_code: str) -> str:
        """Get appropriate court jurisdiction for offense"""
        if statute_code.startswith("IPC"):
            if statute_code in self.mappings:
                return self.mappings[statute_code].get("court", "Unknown Court")
        elif statute_code.startswith("BNS"):
            for ipc, mapping in self.mappings.items():
                if mapping.get("bns_code") == statute_code:
                    return mapping.get("court", "Unknown Court")
        return "Unknown Court"


# Example usage and testing
if __name__ == "__main__":
    resolver = StatuteResolver()

    print("🧪 Testing Statute Resolver:\n")

    # Test IPC → BNS resolution
    print("1. IPC-302 (Murder) → BNS equivalent:")
    result = resolver.resolve_to_bns("IPC-302")
    print(f"   {result}\n")

    # Get punishment
    print("2. Punishment for BNS-103 (Murder):")
    punishment = resolver.get_punishment("BNS-103")
    print(f"   {punishment}\n")

    # Check if cognizable
    print("3. Is IPC-323 (Hurt) cognizable?")
    is_cog = resolver.is_cognizable("IPC-323")
    print(f"   Cognizable: {is_cog}\n")

    # Check if bailable
    print("4. Is BNS-103 (Murder) bailable?")
    is_bail = resolver.is_bailable("BNS-103")
    print(f"   Bailable: {is_bail}\n")

    # Get detailed information
    print("5. Full details for IPC-302:")
    details = resolver.get_statute_details("IPC-302")
    for key, value in details.items():
        print(f"   {key}: {value}")
