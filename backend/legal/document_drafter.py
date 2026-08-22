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
    response_deadline: Optional[str] = None
    
    def __post_init__(self):
        if self.evidence is None:
            self.evidence = []
        if self.witnesses is None:
            self.witnesses = []


@dataclass
class RTIContext:
    """Structured, citizen-reviewed context for an RTI application."""

    applicant_name: str
    applicant_address: str
    applicant_contact: str
    public_authority: str
    subject: str
    information_requests: List[str]
    location: str = ""
    date_range: str = ""
    citizenship_statement: str = "[Confirm citizenship eligibility before filing.]"


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
            "RTI_APPLICATION": self._default_rti_template(),
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
            response_deadline=(
                context.response_deadline
                or "[Insert a legally reviewed response date or period]"
            ),
        )
        
        return notice
    
    def draft_complaint(self, context: CaseContext) -> str:
        """
        Generate the existing generic complaint-petition template.
        
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

    def draft_rti_application(self, context: RTIContext) -> str:
        """Generate an information-seeking RTI application, not a grievance."""
        template = self.templates.get("RTI_APPLICATION", self._default_rti_template())
        numbered_requests = "\n".join(
            f"{index}. {request.strip()}"
            for index, request in enumerate(context.information_requests, 1)
            if request.strip()
        )
        return template.format(
            date=datetime.now().strftime("%d/%m/%Y"),
            applicant_name=context.applicant_name or "[Applicant name required before filing]",
            applicant_address=context.applicant_address or "[Applicant address required before filing]",
            applicant_contact=context.applicant_contact or "[Optional contact details]",
            public_authority=context.public_authority or "[Public authority must be verified]",
            subject=context.subject,
            location=context.location or "[Relevant location, if applicable]",
            date_range=context.date_range or "[Relevant period to be specified]",
            citizenship_statement=context.citizenship_statement,
            information_requests=numbered_requests or "1. [Specify the records or information sought]",
        )
    
    def get_document(self, doc_type: DocumentType, context: CaseContext | RTIContext) -> str:
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
        elif doc_type == DocumentType.RTI_APPLICATION:
            if not isinstance(context, RTIContext):
                raise TypeError("RTI_APPLICATION requires RTIContext")
            return self.draft_rti_application(context)
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

Requested response date or period: {response_deadline}

The legally appropriate response period and proposed next action depend on the
underlying claim, contract, governing law and forum. They must be reviewed before
this notice is sent.

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

    @staticmethod
    def _default_rti_template() -> str:
        """Plain-paper RTI application template using office designations only."""
        return """
RIGHT TO INFORMATION APPLICATION

Date: {date}

To,
The Public Information Officer
{public_authority}

Subject: Request for information under section 6(1) of the Right to Information Act, 2005 - {subject}

Relevant location: {location}
Relevant period: {date_range}

Sir/Madam,

Please provide the following information/records held by or under the control of your public authority:

{information_requests}

Where any part of this request concerns records held by another public authority, please transfer that part in accordance with section 6(3) of the Act and inform me of the transfer. If any requested portion is withheld, please identify the statutory provision relied upon and provide the severable remainder, where applicable.

{citizenship_statement} The requested records may be supplied in electronic form where they are already available in that form.

Applicant:
Name: {applicant_name}
Address: {applicant_address}
Contact: {applicant_contact}

Signature: ____________________
""".strip()
