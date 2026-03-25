"""Jargon Simplifier - Convert legal terminology to plain language."""

from typing import List, Dict, Optional
import json
from pathlib import Path


class JargonSimplifier:
    """Simplify legal jargon into plain language."""
    
    def __init__(self):
        """Initialize with legal glossary."""
        self.glossary = self._load_glossary()
    
    def _load_glossary(self) -> dict:
        """Load legal glossary from JSON."""
        glossary_file = Path(__file__).parent.parent.parent / "data" / "legal_glossary.json"
        try:
            with open(glossary_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return self._default_glossary()
    
    def simplify_term(self, term: str) -> Dict[str, str]:
        """
        Simplify a legal term.
        
        Args:
            term: Legal term to simplify
            
        Returns:
            Dict with simple explanation and examples
        """
        term_lower = term.lower().strip()
        
        # Search in glossary (case-insensitive)
        for key, definition in self.glossary.items():
            if key.lower() == term_lower:
                return {
                    "term": term,
                    "simple_explanation": definition.get("simple", ""),
                    "legal_definition": definition.get("legal", ""),
                    "example": definition.get("example", ""),
                    "hindi_term": definition.get("hindi", ""),
                    "related_terms": definition.get("related", []),
                }
        
        # Not found
        return {
            "term": term,
            "simple_explanation": f"No definition found for '{term}'",
            "legal_definition": "",
            "example": "",
            "hindi_term": "",
            "related_terms": [],
        }
    
    def simplify_statute_code(self, code: str) -> Dict[str, str]:
        """
        Simplify a statute code (e.g., BNS-103).
        
        Args:
            code: BNS or IPC section code
            
        Returns:
            Simple explanation of what this section means
        """
        statute_map = {
            "BNS-103": {
                "title": "Punishment for Murder",
                "simple": "If someone intentionally causes the death of another person, they can be punished with death penalty or life in prison, plus a fine.",
                "hindi": "हत्या के लिए दंड",
                "punishment": "Death or Life Imprisonment + Fine",
            },
            "BNS-115": {
                "title": "Punishment for Voluntarily Causing Hurt",
                "simple": "If someone intentionally causes physical injury to another person, they can face up to 6 months in jail or a fine up to ₹500.",
                "hindi": "स्वेच्छा से चोट पहुँचाने के लिए दंड",
                "punishment": "Up to 6 months jail or ₹500 fine",
            },
            "BNS-303": {
                "title": "Punishment for Theft",
                "simple": "Taking someone else's property without permission can result in up to 7 years in prison or a fine up to ₹250, or both.",
                "hindi": "चोरी के लिए दंड",
                "punishment": "Up to 7 years jail or ₹250 fine",
            },
            "BNS-350": {
                "title": "Punishment for Criminal Intimidation",
                "simple": "Threatening someone to make them afraid or do something they don't want to can result in up to 3 years in jail or a fine up to ₹500.",
                "hindi": "आपराधिक धमकी के लिए दंड",
                "punishment": "Up to 3 years jail or ₹500 fine",
            },
            "BNS-356": {
                "title": "Punishment for Wrongful Restraint",
                "simple": "Holding or confining someone against their will can result in up to 3 months in jail or a fine up to ₹250.",
                "hindi": "अवैध प्रतिबंध के लिए दंड",
                "punishment": "Up to 3 months jail or ₹250 fine",
            },
        }
        
        if code in statute_map:
            stat = statute_map[code]
            return {
                "code": code,
                "title": stat.get("title", ""),
                "simple_explanation": stat.get("simple", ""),
                "hindi": stat.get("hindi", ""),
                "punishment": stat.get("punishment", ""),
            }
        
        # Try IPC mapping (legacy)
        ipc_map = {
            "IPC-302": "Corresponds to BNS-103 (Murder)",
            "IPC-323": "Corresponds to BNS-115 (Hurt)",
            "IPC-379": "Corresponds to BNS-303 (Theft)",
            "IPC-503": "Corresponds to BNS-350 (Criminal Intimidation)",
        }
        
        if code in ipc_map:
            return {
                "code": code,
                "note": "IPC section - now under BNS",
                "equivalent": ipc_map[code],
                "simple_explanation": f"See {ipc_map[code]}",
            }
        
        return {
            "code": code,
            "error": f"Section code '{code}' not found in database",
        }
    
    def simplify_text(self, text: str) -> str:
        """
        Simplify legal text into plain language.
        
        Args:
            text: Legal text to simplify
            
        Returns:
            Simplified version
        """
        simplified = text
        
        # Common legal term replacements
        replacements = {
            "hereinafter": "from now on",
            "aforementioned": "mentioned before",
            "notwithstanding": "despite",
            "pursuant to": "according to",
            "inter alia": "among other things",
            "de facto": "in fact",
            "de jure": "by law",
            "prima facie": "at first sight",
            "habeas corpus": "the right to freedom of person",
            "mens rea": "criminal intent",
            "actus reus": "the criminal act",
        }
        
        for legal_term, simple_term in replacements.items():
            simplified = simplified.replace(legal_term, simple_term)
            simplified = simplified.replace(legal_term.upper(), simple_term.upper())
        
        return simplified
    
    def get_related_terms(self, term: str) -> List[str]:
        """Get related legal terms."""
        term_data = self.simplify_term(term)
        return term_data.get("related_terms", [])
    
    @staticmethod
    def _default_glossary() -> dict:
        """Default legal glossary."""
        return {
            "Accusation": {
                "simple": "When someone claims that another person did something wrong",
                "legal": "A formal charge or claim that a person has committed a crime",
                "example": "The accusation against him was theft from the store",
                "hindi": "आरोप",
                "related": ["Allegation", "Charge"],
            },
            "Acquittal": {
                "simple": "When a court decides you are not guilty",
                "legal": "A judgment rendered by a court that a defendant is not guilty of the charges",
                "example": "After trial, the judge gave an acquittal to the defendant",
                "hindi": "बरी करना",
                "related": ["Not Guilty", "Discharge"],
            },
            "Advocate": {
                "simple": "A lawyer who represents people in court",
                "legal": "A member of the legal profession qualified to appear in court and represent clients",
                "example": "We hired an advocate to help us with the case",
                "hindi": "वकील",
                "related": ["Lawyer", "Attorney", "Counsel"],
            },
            "FIR": {
                "simple": "A written report made to police when a crime is committed",
                "legal": "First Information Report - a formal document lodged with police to initiate criminal investigation",
                "example": "I filed an FIR for theft at the local police station",
                "hindi": "प्रथम सूचना रिपोर्ट",
                "related": ["Police Complaint", "Criminal Complaint"],
            },
            "Evidence": {
                "simple": "Facts or information that help prove what happened",
                "legal": "Any matter, whether oral, documentary, or material, admissible in court to prove a fact",
                "example": "The CCTV footage is strong evidence of the theft",
                "hindi": "सबूत",
                "related": ["Proof", "Testimony", "Document"],
            },
            "Conviction": {
                "simple": "When a court finds someone guilty after trial",
                "legal": "A judgment of a court that a defendant is guilty of a crime",
                "example": "The conviction resulted in a 3-year prison sentence",
                "hindi": "दोषसिद्धि",
                "related": ["Guilty", "Judgment"],
            },
            "Cognizable": {
                "simple": "A crime serious enough that police can arrest without permission",
                "legal": "An offense in which police have power to search, seize, and arrest without warrant",
                "example": "Murder is a cognizable offense, so police can arrest immediately",
                "hindi": "संज्ञेय",
                "related": ["Bailable", "Non-Cognizable"],
            },
            "Bailable": {
                "simple": "A crime where the accused can be released by paying money (bail) until trial",
                "legal": "An offense in which the accused has the right to be released on bail as a matter of right",
                "example": "Theft is a bailable offense, so he was released on ₹10,000 bail",
                "hindi": "जमानती",
                "related": ["Non-Bailable", "Bail"],
            },
            "Witness": {
                "simple": "A person who saw or knows something about what happened",
                "legal": "A person who has seen, heard, or observed something and can testify about it in court",
                "example": "The shop owner was the main witness to the accident",
                "hindi": "गवाह",
                "related": ["Testimony", "Eyewitness"],
            },
            "Grievance": {
                "simple": "A formal complaint about something that is wrong or unfair",
                "legal": "A formal statement of complaint regarding a breach of law or unfair treatment",
                "example": "Filed a grievance about the police's behavior during investigation",
                "hindi": "शिकायत",
                "related": ["Complaint", "Petition"],
            },
            "Mediation": {
                "simple": "When a neutral third person helps two sides reach agreement without court",
                "legal": "A process where parties attempt to resolve their dispute with help of a neutral mediator",
                "example": "The mediator helped us settle the property dispute",
                "hindi": "मध्यस्थता",
                "related": ["Settlement", "Arbitration"],
            },
        }
