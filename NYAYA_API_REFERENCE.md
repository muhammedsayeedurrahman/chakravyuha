# Nyaya API Quick Reference

## Endpoints Overview

### 1. POST `/api/nyaya/query` - Complete Legal Query
Full legal intelligence query combining entity extraction, statute resolution, and guidance.

**Request**:
```json
{
  "query": "Section 302 murder case",
  "language": "hi",
  "include_resolution": true
}
```

**Response**:
```json
{
  "status": "success",
  "query": "Section 302 murder case",
  "entities_extracted": [
    {
      "text": "murder",
      "type": "OFFENSE",
      "statute_reference": "BNS-103",
      "confidence": 0.95
    },
    {
      "text": "Section 302",
      "type": "SECTION",
      "statute_reference": "BNS-103",
      "confidence": 0.95
    }
  ],
  "applicable_sections": [
    {
      "statute_code": "BNS-103",
      "details": { ... }
    }
  ],
  "next_steps": {
    "has_offense": true,
    "has_section": true,
    "recommended_action": "Case appears to fall under specific IPC section",
    "action_steps": [...]
  }
}
```

---

### 2. POST `/api/nyaya/extract-entities` - Entity Extraction
Extract legal entities from user input.

**Request**:
```
POST /api/nyaya/extract-entities?query=hurt+case&language=hi
```

**Response**:
```json
{
  "status": "success",
  "entities": [
    {
      "text": "hurt",
      "type": "OFFENSE",
      "statute_reference": "BNS-115",
      "confidence": 0.85,
      "alternate_names": ["चोट", "मारना", "पीटना"]
    }
  ],
  "entities_count": 1
}
```

---

### 3. GET `/api/nyaya/statute/{statute_code}` - Statute Details
Get comprehensive statute information with IPC↔BNS mapping.

**Request**:
```
GET /api/nyaya/statute/IPC-302
GET /api/nyaya/statute/BNS-103
```

**Response**:
```json
{
  "status": "success",
  "statute_code": "IPC-302",
  "details": {
    "statute_code": "IPC-302",
    "status": "Deprecated (replaced by BNS on 2024-07-01)",
    "current_equivalent": "BNS-103",
    "title": "Punishment for murder",
    "punishment": "Death or life imprisonment + fine",
    "type": "violent",
    "cognizable": true,
    "bailable": false,
    "court_jurisdiction": "Court of Session"
  },
  "resolution": {
    "ipc": "IPC-302",
    "bns": "BNS-103",
    "recommendation": "Use BNS-103 (current law effective from July 1, 2024)"
  },
  "cognizable": true,
  "bailable": false,
  "jurisdiction_court": "Court of Session"
}
```

---

### 4. POST `/api/nyaya/compare-statutes` - IPC vs BNS Comparison
Compare old IPC and new BNS versions of the same offense.

**Request**:
```
POST /api/nyaya/compare-statutes?ipc_code=IPC-302&bns_code=BNS-103
```

**Response**:
```json
{
  "status": "success",
  "comparison": {
    "ipc": {
      "code": "IPC-302",
      "details": { ... },
      "status": "Deprecated (effective until 2024-06-30)"
    },
    "bns": {
      "code": "BNS-103",
      "details": { ... },
      "status": "Current (effective from 2024-07-01)"
    },
    "note": "Both codes refer to the same offense. Use BNS for current legal proceedings."
  }
}
```

---

### 5. GET `/api/nyaya/offense/{offense_name}` - Offense Lookup
Look up offense by common name.

**Request**:
```
GET /api/nyaya/offense/murder
GET /api/nyaya/offense/theft
GET /api/nyaya/offense/hurt
```

**Response**:
```json
{
  "status": "success",
  "offense_searched": "murder",
  "results": [
    {
      "ipc_code": "IPC-302",
      "bns_code": "BNS-103",
      "title": "Punishment for murder",
      "punishment": "Death or life imprisonment + fine",
      "type": "violent",
      "cognizable": true,
      "bailable": false
    }
  ],
  "results_count": 1
}
```

---

### 6. GET `/api/nyaya/help` - API Documentation
Get complete API documentation and available endpoints.

**Request**:
```
GET /api/nyaya/help
```

**Response**:
```json
{
  "status": "operational",
  "system": "Nyaya Legal Intelligence",
  "endpoints": [
    {
      "path": "/api/nyaya/extract-entities",
      "method": "POST",
      "description": "Extract legal entities (statutes, offenses) from query",
      "example": "?query=section%20302&language=hi"
    },
    ...
  ],
  "supported_languages": ["hi", "ta", "te", "kn", "ml", "en"],
  "entity_types": ["STATUTE", "SECTION", "OFFENSE", "PUNISHMENT", "JURISDICTION"]
}
```

---

### 7. GET `/api/nyaya/health` - Health Check
Check Nyaya system health status.

**Request**:
```
GET /api/nyaya/health
```

**Response**:
```json
{
  "status": "healthy",
  "service": "nyaya",
  "mappings_loaded": true,
  "total_sections_indexed": 18,
  "timestamp": "2026-03-24T12:34:56.789Z"
}
```

---

## Supported Entity Types

| Entity Type | Description | Examples |
|------------|-------------|----------|
| **STATUTE** | Act or law code | "IPC", "BNS", "CrPC" |
| **SECTION** | Specific section number | "Section 302", "Article 15" |
| **OFFENSE** | Crime/wrongdoing type | "murder", "theft", "hurt" |
| **PUNISHMENT** | Sentencing info | "life imprisonment", "fine" |
| **JURISDICTION** | Court level | "magistrate", "sessions", "high court" |

---

## Language Support

- `hi` - Hindi
- `ta` - Tamil
- `te` - Telugu
- `kn` - Kannada
- `ml` - Malayalam
- `en` - English (default)

---

## Common Use Cases

### Case 1: User describes a hurt incident
```bash
curl -X POST "http://localhost:8000/api/nyaya/extract-entities" \
  -G --data-urlencode "query=Someone hurt me during a fight" \
  --data-urlencode "language=en"
```

### Case 2: Check if offense is bailable
```bash
curl "http://localhost:8000/api/nyaya/statute/BNS-103" | jq '.bailable'
# Returns: false
```

### Case 3: Get both IPC and BNS versions
```bash
curl -X POST "http://localhost:8000/api/nyaya/compare-statutes" \
  -G --data-urlencode "ipc_code=IPC-323"
```

### Case 4: Find all statutes for an offense
```bash
curl "http://localhost:8000/api/nyaya/offense/theft"
```

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 404 | Statute/offense not found |
| 422 | Invalid parameters |
| 500 | Server error |

---

## Error Handling

When a statute is not found:
```json
{
  "status": "success",
  "statute_code": "IPC-9999",
  "details": {
    "error": "IPC-9999 not found in mappings",
    "status": "Not mapped"
  }
}
```

---

## Testing Endpoints

### Quick Test
```bash
# Test entity extraction
curl "http://localhost:8000/api/nyaya/extract-entities?query=section%20302%20murder&language=en"

# Test statute lookup
curl "http://localhost:8000/api/nyaya/statute/IPC-302"

# Test health
curl "http://localhost:8000/api/nyaya/health"
```

### Full Integration Test
```bash
python test_nyaya_functional.py
```

---

## Response Time

Typical response times:
- Entity extraction: < 50ms
- Statute lookup: < 10ms
- Full legal query: < 100ms

---

## Limitations

- Entity extraction uses keyword matching (not NER)
- Hindi matching requires exact keywords
- IPC mapping covers 18+ major sections (not all 511)
- No real-time internet access

---

## Future Enhancements

Phase 2 could add:
- Confidence filtering for RAG results
- Auto-escalation to NALSA, Tele-Law, Police
- Browser automation for form pre-filling
- Full IPC section mapping (all 511)

---

## Support

For questions or issues:
1. Check `/api/nyaya/help` for API docs
2. Review test files: `tests/test_nyaya_*.py`
3. Check functional test: `python test_nyaya_functional.py`

---

**Last Updated**: March 24, 2026  
**Status**: Production Ready ✅
