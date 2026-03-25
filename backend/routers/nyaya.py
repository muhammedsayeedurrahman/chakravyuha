"""
Nyaya Routes - Legal intelligence API endpoints

Provides high-level legal query endpoints that combine:
- Entity extraction (statutes, offenses, jurisdiction)
- Statute resolution (IPC ↔ BNS mapping)
- RAG retrieval with entity filtering
- Auto-escalation routing to government services
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import Optional, List
from datetime import datetime
import os

from backend.legal.nyaya_extractor import NyayaEntityExtractor, EntityType
from backend.legal.statute_resolver import StatuteResolver

router = APIRouter(prefix="/api/nyaya", tags=["nyaya"])

# Initialize Nyaya components
entity_extractor = NyayaEntityExtractor()
statute_resolver = StatuteResolver()


@router.post("/extract-entities")
async def extract_legal_entities(query: str, language: str = "hi"):
    """
    Extract legal entities (statutes, offenses, jurisdiction) from query text
    
    Args:
        query: User query in English or regional language
        language: Language code (hi, ta, te, kn, ml, etc.)
    
    Returns:
        List of extracted entities with confidence scores
    
    Example:
        POST /api/nyaya/extract-entities?query=mere%20sath%20marof%20hua&language=hi
    """
    try:
        entities = entity_extractor.extract(query, language)
        
        return {
            "status": "success",
            "query": query,
            "language": language,
            "entities_count": len(entities),
            "entities": [
                {
                    "text": e.text,
                    "type": e.entity_type.value,
                    "statute_reference": e.statute_reference,
                    "confidence": round(e.confidence, 2),
                    "alternate_names": e.alternate_names,
                }
                for e in entities
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Entity extraction failed: {str(e)}")


@router.get("/statute/{statute_code}")
async def get_statute_resolve(statute_code: str):
    """
    Get statute information with IPC ↔ BNS mapping
    
    Args:
        statute_code: IPC code (e.g., IPC-302) or BNS code (e.g., BNS-103)
    
    Returns:
        Statute details with equivalent code and punishment information
    
    Example:
        GET /api/nyaya/statute/IPC-302
        GET /api/nyaya/statute/BNS-103
    """
    try:
        details = statute_resolver.get_statute_details(statute_code)
        
        if "error" in details:
            raise HTTPException(status_code=404, detail=details["error"])
        
        # Add additional computed fields
        if statute_code.startswith("IPC"):
            resolution = statute_resolver.resolve_to_bns(statute_code)
        else:
            resolution = statute_resolver.resolve_to_ipc(statute_code)
        
        return {
            "status": "success",
            "statute_code": statute_code,
            "details": details,
            "resolution": resolution,
            "cognizable": statute_resolver.is_cognizable(statute_code),
            "bailable": statute_resolver.is_bailable(statute_code),
            "jurisdiction_court": statute_resolver.get_jurisdiction_court(statute_code),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Statute lookup failed: {str(e)}")


@router.post("/compare-statutes")
async def compare_statutes(ipc_code: str, bns_code: Optional[str] = None):
    """
    Compare IPC and BNS versions of the same offense
    
    Args:
        ipc_code: IPC section code (e.g., IPC-302)
        bns_code: Optional BNS code (if not provided, automatically resolved)
    
    Returns:
        Side-by-side comparison
    
    Example:
        POST /api/nyaya/compare-statutes?ipc_code=IPC-302&bns_code=BNS-103
    """
    try:
        ipc_details = statute_resolver.get_statute_details(ipc_code)
        
        if "error" in ipc_details:
            raise HTTPException(status_code=404, detail=f"{ipc_code} not found")
        
        # Get BNS equivalent if not provided
        if not bns_code:
            bns_code = ipc_details.get("statute_code", "")
            if ipc_code.startswith("IPC"):
                resolution = statute_resolver.resolve_to_bns(ipc_code)
                bns_code = resolution.get("bns", "")
        
        bns_details = statute_resolver.get_statute_details(bns_code)
        
        if "error" in bns_details:
            raise HTTPException(status_code=404, detail=f"{bns_code} not found")
        
        return {
            "status": "success",
            "comparison": {
                "ipc": {
                    "code": ipc_code,
                    "details": ipc_details,
                    "status": "Deprecated (effective until 2024-06-30)"
                },
                "bns": {
                    "code": bns_code,
                    "details": bns_details,
                    "status": "Current (effective from 2024-07-01)"
                },
                "note": "Both codes refer to the same offense. Use BNS for current legal proceedings."
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.get("/offense/{offense_name}")
async def lookup_offense(offense_name: str):
    """
    Look up offense by common name and get applicable sections
    
    Args:
        offense_name: Common name like "murder", "theft", "hurt", etc.
    
    Returns:
        Applicable IPC and BNS sections with details
    
    Example:
        GET /api/nyaya/offense/murder
    """
    try:
        offense_lower = offense_name.lower()
        results = []
        
        # Find all mappings that match this offense
        for ipc_code, mapping in entity_extractor.mappings.items():
            title = mapping.get("title", "").lower()
            if offense_lower in title or title.startswith(offense_lower):
                bns_code = mapping.get("bns_code", "")
                results.append({
                    "ipc_code": ipc_code,
                    "bns_code": bns_code,
                    "title": mapping.get("title", ""),
                    "punishment": mapping.get("punishment", ""),
                    "type": mapping.get("type", ""),
                    "cognizable": mapping.get("cognizable", False),
                    "bailable": mapping.get("bailable", True),
                })
        
        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"No offenses found matching '{offense_name}'"
            )
        
        return {
            "status": "success",
            "offense_searched": offense_name,
            "results_count": len(results),
            "results": results,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Offense lookup failed: {str(e)}")


@router.post("/query")
async def legal_query(
    query: str,
    language: str = "hi",
    include_resolution: bool = True
):
    """
    Complete legal intelligence query
    
    Combines entity extraction, statute resolution, and legal guidance
    
    Args:
        query: User query in English or regional language
        language: Language code (default: Hindi)
        include_resolution: Include IPC ↔ BNS resolution (default: true)
    
    Returns:
        Comprehensive legal response with entities and applicable sections
    
    Example:
        POST /api/nyaya/query
        {
            "query": "Mere sath marof hua",
            "language": "hi"
        }
    """
    try:
        # Step 1: Extract entities
        entities = entity_extractor.extract(query, language)
        entities_dict = [
            {
                "text": e.text,
                "type": e.entity_type.value,
                "statute_reference": e.statute_reference,
                "confidence": round(e.confidence, 2),
            }
            for e in entities
        ]
        
        # Step 2: If sections found, get their details
        applicable_sections = []
        for entity in entities:
            if entity.entity_type == EntityType.SECTION:
                details = statute_resolver.get_statute_details(entity.statute_reference)
                if "error" not in details:
                    applicable_sections.append({
                        "statute_code": entity.statute_reference,
                        "details": details,
                    })
        
        # Step 3: Build response
        response = {
            "status": "success",
            "query": query,
            "language": language,
            "timestamp": datetime.utcnow().isoformat(),
            "entities_extracted": entities_dict,
            "entities_count": len(entities_dict),
            "applicable_sections": applicable_sections,
            "next_steps": generate_guidance(entities)
        }
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")


@router.get("/help")
async def system_help():
    """
    Nyaya system help and documentation
    
    Returns information about available endpoints and how to use them
    """
    return {
        "status": "operational",
        "system": "Nyaya Legal Intelligence",
        "version": "1.0",
        "description": "Legal AI for Indian justice system",
        "endpoints": [
            {
                "path": "/api/nyaya/extract-entities",
                "method": "POST",
                "description": "Extract legal entities (statutes, offenses) from query",
                "example": "?query=section%20302&language=hi"
            },
            {
                "path": "/api/nyaya/statute/{statute_code}",
                "method": "GET",
                "description": "Get statute details with IPC↔BNS mapping",
                "example": "/api/nyaya/statute/IPC-302"
            },
            {
                "path": "/api/nyaya/compare-statutes",
                "method": "POST",
                "description": "Compare IPC and BNS versions",
                "example": "?ipc_code=IPC-302&bns_code=BNS-103"
            },
            {
                "path": "/api/nyaya/offense/{offense_name}",
                "method": "GET",
                "description": "Look up offense by name",
                "example": "/api/nyaya/offense/murder"
            },
            {
                "path": "/api/nyaya/query",
                "method": "POST",
                "description": "Complete legal intelligence query",
                "example": '{"query": "mere sath marof hua", "language": "hi"}'
            },
            {
                "path": "/api/nyaya/help",
                "method": "GET",
                "description": "Show this help message"
            }
        ],
        "supported_languages": ["hi", "ta", "te", "kn", "ml", "en"],
        "statute_types": ["IPC", "BNS", "CrPC"],
        "entity_types": ["STATUTE", "SECTION", "OFFENSE", "PUNISHMENT", "JURISDICTION"],
    }


def generate_guidance(entities: List) -> dict:
    """Generate next steps guidance based on extracted entities"""
    guidance = {
        "has_offense": False,
        "has_section": False,
        "recommended_action": "",
        "action_steps": []
    }
    
    for entity in entities:
        if entity.entity_type == EntityType.OFFENSE:
            guidance["has_offense"] = True
        if entity.entity_type == EntityType.SECTION:
            guidance["has_section"] = True
    
    if guidance["has_offense"] and guidance["has_section"]:
        guidance["recommended_action"] = "Case appears to fall under specific IPC section"
        guidance["action_steps"] = [
            "1. Consult the applicable section details above",
            "2. Contact a lawyer for legal advice",
            "3. If applicable, file reports with appropriate authority"
        ]
    elif guidance["has_offense"]:
        guidance["recommended_action"] = "Potential legal offense identified"
        guidance["action_steps"] = [
            "1. Seek legal consultation immediately",
            "2. Gather evidence and documentation",
            "3. Contact local police station if needed"
        ]
    else:
        guidance["recommended_action"] = "No specific legal offense identified"
        guidance["action_steps"] = [
            "1. Provide more details about the situation",
            "2. Specify the section of law if known",
            "3. Consult a legal professional for guidance"
        ]
    
    return guidance


# HealthCheck endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Verify data files are loaded
        mappings_loaded = len(entity_extractor.mappings) > 0
        
        return {
            "status": "healthy" if mappings_loaded else "unhealthy",
            "service": "nyaya",
            "mappings_loaded": mappings_loaded,
            "total_sections_indexed": len(entity_extractor.mappings),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "nyaya",
            "error": str(e)
        }
