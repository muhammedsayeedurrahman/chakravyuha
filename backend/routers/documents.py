"""FastAPI router for document generation endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

from backend.legal.document_drafter import DocumentDrafter, DocumentType, PartyInfo, CaseContext
from backend.agent.complaint_drafter_agent import ComplaintDrafterAgent

router = APIRouter(prefix="/api/documents", tags=["Documents"])
drafter = DocumentDrafter()
_complaint_agent = ComplaintDrafterAgent()


# ── Request/Response Models ────────────────────────────────────────────────

class PartyRequest(BaseModel):
    """Party information for documents."""
    name: str = Field(..., description="Full name")
    phone: str = Field(..., description="Contact phone")
    email: Optional[EmailStr] = None
    address: str = Field(default="", description="Full address")
    occupation: Optional[str] = None


class DocumentGenerationRequest(BaseModel):
    """Request to generate a legal document."""
    document_type: str = Field(..., description="FIR, LEGAL_NOTICE, or COMPLAINT")
    complainant: PartyRequest
    accused: PartyRequest
    case_type: str = Field(..., description="Type of case (e.g., Theft, Assault)")
    incident_date: str = Field(..., description="YYYY-MM-DD format")
    incident_location: str
    description: str = Field(..., description="Detailed narrative of incident")
    offense_sections: List[str] = Field(..., description="BNS section codes")
    evidence: Optional[List[str]] = []
    witnesses: Optional[List[str]] = []


class DocumentResponse(BaseModel):
    """Response with generated document."""
    document_type: str
    content: str
    generated_at: str
    status: str = "success"


class DocumentPreviewResponse(BaseModel):
    """Preview of document before generation."""
    document_type: str
    parties_summary: dict
    sections: List[str]
    case_summary: str
    estimated_length: str


class AutoDraftRequest(BaseModel):
    """Request for agentic auto-drafting from narrative text."""

    narrative: str = Field(
        ...,
        description="Free-text description of the incident",
        min_length=10,
    )
    complainant_name: str = Field(default="", description="Name of the person filing")
    complainant_phone: str = Field(default="", description="Phone number")
    complainant_address: str = Field(default="", description="Address")
    complainant_email: Optional[str] = Field(default="", description="Email")
    accused_name: str = Field(default="", description="Name of accused (auto-extracted if empty)")
    accused_phone: str = Field(default="", description="Phone of accused")
    accused_address: str = Field(default="", description="Address of accused")
    preferred_document_type: str = Field(
        default="",
        description="Force FIR / LEGAL_NOTICE / COMPLAINT (auto-classified if empty)",
    )
    language: str = Field(default="en-IN", description="Language code (e.g., hi-IN, en-IN)")


class AutoDraftResponse(BaseModel):
    """Response from the agentic auto-draft pipeline."""

    status: str  # "success" | "needs_info" | "error"
    document_type: str
    content: str
    applicable_sections: List[str]
    extracted_offense: str
    offense_confidence: float
    jurisdiction: str
    punishment_summary: str
    cognizable: bool
    bailable: bool
    strategy: Optional[dict] = None
    missing_fields: List[str]
    generated_at: str
    error: Optional[str] = None


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/auto-draft", response_model=AutoDraftResponse)
async def auto_draft(request: AutoDraftRequest):
    """
    Agentic auto-draft: provide a narrative, get a complete legal document.

    The agent automatically:
    1. Extracts offense type, applicable BNS/IPC sections
    2. Classifies the best document type (FIR / Legal Notice / Complaint)
    3. Generates a professional, court-ready document using LLM
    4. Provides legal strategy with next steps and cost estimates

    **Example request** (minimal — just a narrative):
    ```json
    {
        "narrative": "My neighbor stole my mobile phone from my house on March 20th. I saw him running away with it.",
        "complainant_name": "Raj Kumar",
        "complainant_phone": "9876543210"
    }
    ```

    **Example response**:
    ```json
    {
        "status": "success",
        "document_type": "FIR",
        "content": "... (complete FIR document) ...",
        "applicable_sections": ["BNS-303"],
        "extracted_offense": "theft",
        "offense_confidence": 0.90,
        "jurisdiction": "Police Station (FIR)",
        "strategy": { ... },
        "missing_fields": []
    }
    ```
    """
    try:
        result = _complaint_agent.auto_draft(
            narrative=request.narrative,
            complainant_name=request.complainant_name,
            complainant_phone=request.complainant_phone,
            complainant_address=request.complainant_address,
            complainant_email=request.complainant_email or "",
            accused_name=request.accused_name,
            accused_phone=request.accused_phone,
            accused_address=request.accused_address,
            preferred_doc_type=request.preferred_document_type,
            language=request.language,
        )

        extracted = result.extracted_info
        return AutoDraftResponse(
            status=result.status,
            document_type=result.document_type,
            content=result.content,
            applicable_sections=list(result.applicable_sections),
            extracted_offense=extracted.offense if extracted else "",
            offense_confidence=result.confidence,
            jurisdiction=extracted.jurisdiction if extracted else "",
            punishment_summary=extracted.punishment_summary if extracted else "",
            cognizable=extracted.cognizable if extracted else False,
            bailable=extracted.bailable if extracted else True,
            strategy=result.strategy_summary,
            missing_fields=list(result.missing_fields),
            generated_at=result.generated_at,
            error=result.error,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Auto-draft failed: {str(e)}",
        )


@router.post("/draft-fir", response_model=DocumentResponse)
async def draft_fir(request: DocumentGenerationRequest):
    """
    Generate a First Information Report (FIR).
    
    **Use case**: Police complaint for criminal case
    **Output**: Ready-to-file FIR document
    
    **Example request**:
    ```json
    {
        "document_type": "FIR",
        "complainant": {
            "name": "Raj Kumar",
            "phone": "9876543210",
            "address": "123 Main Street, Delhi"
        },
        "accused": {
            "name": "John Doe",
            "phone": "9123456789",
            "address": "456 Court Road, Delhi"
        },
        "case_type": "Theft",
        "incident_date": "2024-03-20",
        "incident_location": "Delhi",
        "description": "My mobile phone was stolen...",
        "offense_sections": ["BNS-303"]
    }
    ```
    """
    try:
        context = _create_context(request)
        fir_content = drafter.draft_fir(context)
        
        return DocumentResponse(
            document_type="FIR",
            content=fir_content,
            generated_at=datetime.now().isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"FIR generation failed: {str(e)}")


@router.post("/draft-legal-notice", response_model=DocumentResponse)
async def draft_legal_notice(request: DocumentGenerationRequest):
    """
    Generate a legal notice (sent before FIR).
    
    **Use case**: Formal warning to accused before filing FIR
    **Output**: Formatted legal notice
    
    A legal notice is often sent first to give the accused time to respond 
    or settle the matter out of court.
    """
    try:
        context = _create_context(request)
        notice_content = drafter.draft_legal_notice(context)
        
        return DocumentResponse(
            document_type="LEGAL_NOTICE",
            content=notice_content,
            generated_at=datetime.now().isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Legal notice generation failed: {str(e)}")


@router.post("/draft-complaint", response_model=DocumentResponse)
async def draft_complaint(request: DocumentGenerationRequest):
    """
    Generate a consumer/civil complaint.
    
    **Use case**: Consumer disputes, civil matters
    **Output**: Complaint petition ready for filing
    
    Use this for consumer complaints or civil cases, not criminal complaints.
    """
    try:
        context = _create_context(request)
        complaint_content = drafter.draft_complaint(context)
        
        return DocumentResponse(
            document_type="COMPLAINT",
            content=complaint_content,
            generated_at=datetime.now().isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Complaint generation failed: {str(e)}")


@router.post("/preview", response_model=DocumentPreviewResponse)
async def preview_document(request: DocumentGenerationRequest):
    """
    Preview a document before full generation.
    
    **Use case**: Verify details are correct before generating
    **Output**: Summary of what will be generated
    """
    try:
        return DocumentPreviewResponse(
            document_type=request.document_type,
            parties_summary={
                "complainant": request.complainant.name,
                "accused": request.accused.name,
            },
            sections=request.offense_sections,
            case_summary=request.description[:100] + "..." if len(request.description) > 100 else request.description,
            estimated_length="2-4 pages",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Preview failed: {str(e)}")


@router.get("/templates")
async def list_templates():
    """List all available document templates."""
    return {
        "templates": [
            {
                "name": "FIR",
                "description": "First Information Report for criminal cases",
                "use_case": "Police complaint",
            },
            {
                "name": "LEGAL_NOTICE",
                "description": "Legal notice sent before filing FIR",
                "use_case": "Pre-FIR formal notice",
            },
            {
                "name": "COMPLAINT",
                "description": "Complaint petition for civil/consumer cases",
                "use_case": "Consumer disputes, civil matters",
            },
        ]
    }


@router.get("/help")
async def document_help():
    """Get help about document generation."""
    return {
        "help": "Use the /api/documents endpoints to generate legal documents",
        "endpoints": [
            {
                "method": "POST",
                "path": "/api/documents/auto-draft",
                "description": "AI-powered auto-draft from narrative (recommended)",
            },
            {
                "method": "POST",
                "path": "/api/documents/draft-fir",
                "description": "Generate FIR (manual fields)",
            },
            {
                "method": "POST",
                "path": "/api/documents/draft-legal-notice",
                "description": "Generate legal notice (manual fields)",
            },
            {
                "method": "POST",
                "path": "/api/documents/draft-complaint",
                "description": "Generate complaint (manual fields)",
            },
        ],
    }


# ── Helper Functions ───────────────────────────────────────────────────────

def _create_context(request: DocumentGenerationRequest) -> CaseContext:
    """Convert API request to CaseContext."""
    return CaseContext(
        complainant=PartyInfo(
            name=request.complainant.name,
            phone=request.complainant.phone,
            email=request.complainant.email,
            address=request.complainant.address,
            occupation=request.complainant.occupation,
        ),
        accused=PartyInfo(
            name=request.accused.name,
            phone=request.accused.phone,
            address=request.accused.address,
        ),
        case_type=request.case_type,
        incident_date=request.incident_date,
        incident_location=request.incident_location,
        description=request.description,
        offense_sections=request.offense_sections,
        evidence=request.evidence or [],
        witnesses=request.witnesses or [],
    )
