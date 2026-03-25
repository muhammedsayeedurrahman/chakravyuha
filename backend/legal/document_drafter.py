"""Document Drafting Agent - Generate FIR, legal notices, complaints."""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum
import json
import os
from datetime import datetime
from pathlib import Path


class DocumentType(Enum):
    """Types of legal documents."""
    FIR = "FIR"
    LEGAL_NOTICE = "LEGAL_NOTICE"
    COMPLAINT = "COMPLAINT"
    RTI_APPLICATION = "RTI_APPLICATION"


@dataclass
class PartyInfo:
    """Information about a party (complainant/accused)."""
    name: str
    phone: str
    email: Optional[str] = None
    address: str = ""
    occupation: Optional[str] = None


@dataclass
class CaseContext:
    """Case context for document generation."""
    complainant: PartyInfo
    accused: PartyInfo
    case_type: str  # e.g., "Theft", "Assault", "Cheating"
    incident_date: str  # YYYY-MM-DD format
    incident_location: str
    description: str  # Detailed narrative
    offense_sections: List[str]  # e.g., ["BNS-315", "BNS-350"]
    evidence: List[str] = None
    witnesses: List[str] = None
    
    def __post_init__(self):
        if self.evidence is None:
            self.evidence = []
        if self.witnesses is None:
            self.witnesses = []


class DocumentDrafter:
    """Generate legal documents from case context."""
    
    def __init__(self):
        """Initialize document drafter with templates."""
        self.templates = self._load_templates()
    
    def _load_templates(self) -> dict:
        """Load document templates."""
        # Use built-in templates
        return {
            "FIR": self._default_fir_template(),
            "LEGAL_NOTICE": self._default_notice_template(),
            "COMPLAINT": self._default_complaint_template(),
        }
    
    def draft_fir(self, context: CaseContext) -> str:
        """
        Generate an FIR (First Information Report).
        
        Args:
            context: Case context with parties, incident details, offenses
            
        Returns:
            Formatted FIR document as string
        """
        template = self.templates.get("FIR", self._default_fir_template())
        
        fir = template.format(
            date=datetime.now().strftime("%d/%m/%Y"),
            time=datetime.now().strftime("%H:%M"),
            complainant_name=context.complainant.name,
            complainant_phone=context.complainant.phone,
            complainant_address=context.complainant.address,
            accused_name=context.accused.name,
            accused_address=context.accused.address,
            incident_date=context.incident_date,
            incident_location=context.incident_location,
            case_type=context.case_type,
            description=context.description,
            offense_sections=", ".join(context.offense_sections),
            evidence_list="\n".join(f"  • {e}" for e in context.evidence) if context.evidence else "  (To be collected)",
            witnesses_list="\n".join(f"  • {w}" for w in context.witnesses) if context.witnesses else "  (To be identified)",
        )
        
        return fir
    
    def draft_legal_notice(self, context: CaseContext) -> str:
        """
        Generate a legal notice (sent to accused before FIR).
        
        Args:
            context: Case context
            
        Returns:
            Formatted legal notice as string
        """
        template = self.templates.get("LEGAL_NOTICE", self._default_notice_template())
        
        notice = template.format(
            date=datetime.now().strftime("%d/%m/%Y"),
            complainant_name=context.complainant.name,
            complainant_address=context.complainant.address,
            accused_name=context.accused.name,
            accused_address=context.accused.address,
            incident_location=context.incident_location,
            incident_date=context.incident_date,
            case_description=context.description,
            case_type=context.case_type,
            offense_sections=", ".join(context.offense_sections),
        )
        
        return notice
    
    def draft_complaint(self, context: CaseContext) -> str:
        """
        Generate a consumer complaint or civil complaint.
        
        Args:
            context: Case context
            
        Returns:
            Formatted complaint as string
        """
        template = self.templates.get("COMPLAINT", self._default_complaint_template())
        
        complaint = template.format(
            date=datetime.now().strftime("%d/%m/%Y"),
            complainant_name=context.complainant.name,
            complainant_phone=context.complainant.phone,
            complainant_email=context.complainant.email or "Not provided",
            accused_name=context.accused.name,
            incident_date=context.incident_date,
            incident_description=context.description,
            relief_sought="Appropriate relief as per law",
            offense_sections=", ".join(context.offense_sections),
        )
        
        return complaint
    
    def get_document(self, doc_type: DocumentType, context: CaseContext) -> str:
        """
        Get document based on type.
        
        Args:
            doc_type: Type of document to generate
            context: Case context
            
        Returns:
            Generated document as string
        """
        if doc_type == DocumentType.FIR:
            return self.draft_fir(context)
        elif doc_type == DocumentType.LEGAL_NOTICE:
            return self.draft_legal_notice(context)
        elif doc_type == DocumentType.COMPLAINT:
            return self.draft_complaint(context)
        else:
            raise ValueError(f"Unknown document type: {doc_type}")
    
    @staticmethod
    def _default_fir_template() -> str:
        """Default FIR template."""
        return """
================================================================================
                        FIRST INFORMATION REPORT (FIR)
================================================================================

Report Filed Date: {date}
Report Filed Time: {time}

REPORTER (COMPLAINANT) DETAILS:
────────────────────────────────
Name:               {complainant_name}
Phone:              {complainant_phone}
Address:            {complainant_address}

ACCUSED DETAILS:
────────────────────────────────
Name:               {accused_name}
Address:            {accused_address}

INCIDENT DETAILS:
────────────────────────────────
Date of Incident:   {incident_date}
Place of Incident:  {incident_location}
Type of Case:       {case_type}

DESCRIPTION OF INCIDENT:
────────────────────────────────
{description}

APPLICABLE SECTIONS OF BNS:
────────────────────────────────
{offense_sections}

EVIDENCE:
────────────────────────────────
{evidence_list}

WITNESSES:
────────────────────────────────
{witnesses_list}

================================================================================
[To be signed by: Police Officer / Judicial Magistrate]
================================================================================
"""
    
    @staticmethod
    def _default_notice_template() -> str:
        """Default legal notice template."""
        return """
================================================================================
                        LEGAL NOTICE
================================================================================

Date: {date}

TO,
{accused_name}
{accused_address}

FROM,
{complainant_name}
{complainant_address}

SUBJECT: LEGAL NOTICE FOR {case_type}

DEAR SIR/MADAM,

NOTICE IS HEREBY GIVEN that you have committed the following act(s), which are 
in violation of provisions of the Bharatiya Nyaya Sanhita (BNS) and the same 
has caused loss/injury to my client.

PARTICULARS OF INCIDENT:
────────────────────────────────
Date:               {incident_date}
Location:           {incident_location}
Offense Sections:   {offense_sections}

DETAILS OF INCIDENT:
────────────────────────────────
{case_description}

DEMAND:
────────────────────────────────
My client demands that you:

1. Desist and cease from committing the aforesaid acts
2. Pay compensation for damages (if applicable)
3. Refrain from causing further loss/injury

You are required to comply with this notice within 30 (Thirty) days of 
receipt of this notice. In case of non-compliance, legal action will be 
initiated against you without any further notice.

Yours faithfully,

{complainant_name}
Date: {date}

[Counsel's Signature & Seal - to be added when filed]

================================================================================
"""
    
    @staticmethod
    def _default_complaint_template() -> str:
        """Default complaint template."""
        return """
================================================================================
                        COMPLAINT PETITION
================================================================================

Date: {date}

COMPLAINANT DETAILS:
────────────────────────────────
Name:               {complainant_name}
Phone:              {complainant_phone}
Email:              {complainant_email}

AGAINST:
────────────────────────────────
Name:               {accused_name}

INCIDENT DETAILS:
────────────────────────────────
Date of Incident:   {incident_date}
Description:        {incident_description}

APPLICABLE LAW:
────────────────────────────────
Sections:           {offense_sections}

RELIEF SOUGHT:
────────────────────────────────
{relief_sought}

PRAYER:
────────────────────────────────
It is most humbly prayed that this Ld. Court may be pleased to:

1. Direct investigation into the allegations
2. Register appropriate case against the accused person(s)
3. Grant such further or other relief as may be deemed fit and proper

VERIFICATION:
────────────────────────────────
I, {complainant_name}, hereby verify that the facts stated above are true 
to my knowledge and belief. I undertake to support this complaint with 
necessary evidence.

Dated: {date}

Signature: _____________________
(Complainant)

================================================================================
"""
