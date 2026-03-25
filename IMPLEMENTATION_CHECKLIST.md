# Implementation Checklist - Nyaya × Chakravyuha

**Status**: Ready for implementation  
**Phaokayse**: Enhanced Phase 1 → Phase 2  
**Priority**: CRITICAL (ASR testing) → HIGH (Nyaya layer) → MEDIUM (Escalation)

---

## 📋 Immediate Action Items (Track Progress)

### CRITICAL - This Week (Unblock Core Testing)

- [ ] **1.1** Fix Sarvam ASR provider credentials
  - File: `backend/services/llm/sarvam_provider.py`
  - Issue: Need valid API key for real voice testing
  - Action: Test with sample Hindi/Tamil audio files
  - Impact: Unblocks all ASR+TTS integration tests

- [ ] **1.2** Build legal corpus index
  - File: `data/ipc_sections.json` (expand from 350 → 500+ sections)
  - Source: indiacode.nic.in + Indian Kanoon
  - Action: Run `scripts/build_augmented_index.py`
  - Impact: RAG retrieval for all sections

- [ ] **1.3** Test RAG accuracy on 20 sample queries
  - File: `tests/test_rag.py` (enhance)
  - Expected: >85% top-1 accuracy
  - Action: Add entity-based filtering to boost accuracy
  - Definition of done: 17/20 queries correct (>85%)

---

### HIGH - Week 2 (Add Nyaya Intelligence)

- [ ] **2.1** Create NyayaEntityExtractor class
  - New file: `backend/legal/nyaya_extractor.py`
  - Classes: `NyayaEntity`, `EntityType` (enum), `NyayaEntityExtractor`
  - Test file: `tests/test_nyaya_extractor.py`
  - Target: Extract [STATUTE, SECTION, OFFENSE, PUNISHMENT, JURISDICTION]

- [ ] **2.2** Build IPC↔BNS mapping table
  - New file: `data/ipc_bns_mapping.json`
  - Content: 511 IPC sections → BNS equivalents
  - Format: `{"IPC-302": {"bns": "BNS-103", "title": "Murder"}, ...}`
  - Test: `tests/test_statute_resolver.py`

- [ ] **2.3** Create StatuteResolver class
  - New file: `backend/legal/statute_resolver.py`
  - Method: `resolve_ipc_to_bns(ipc_code)` → BNS code
  - Handles transition: IPC expiration (July 1, 2023)
  - Test: Verify all 511 mappings

- [ ] **2.4** Create ConfidenceFilter class
  - New file: `backend/legal/confidence_filter.py`
  - Method: `filter_rag_results()` → high/medium/low confidence tiers
  - Threshold logic: >0.85 (high), 0.70-0.85 (medium), <0.70 (low)
  - Integration: Call in RAG retrieval pipeline

- [ ] **2.5** Integrate entity extraction into RAG pipeline
  - File: `backend/legal/rag.py` (modify)
  - Change: `query_legal_db(query)` → `query_legal_db(query, entities)`
  - Impact: Boost RAG accuracy from 75% → 85%+
  - Test: test_rag.py should pass at >85%

---

### MEDIUM - Week 3 (Add Auto-Escalation)

- [ ] **3.1** Create EscalationRouter class
  - New file: `backend/agent/escalation_router.py`
  - Classes: `EscalationType` (enum), `EscalationRouter`
  - Methods: `classify_and_route()`, `_determine_escalation()`
  - Routes: POLICE_FIR, NALSA_LEGAL_AID, TELE_LAW, eCOURTS

- [ ] **3.2** Load gov portal endpoints
  - New file: `data/escalation_rules.json`
  - Content: Portal URLs, contact numbers, eligibility rules
  - Format: `{"POLICE_FIR": "https://ict.police.gov.in/", ...}`

- [ ] **3.3** Load NALSA office locations
  - New file: `data/nalsa_offices.json`
  - Content: 36 state/UT offices + contact info
  - Format: `[{"state": "Gujarat", "city": "Ahmedabad", "phone": "..."}]`
  - Method in router: `find_nalsa_office(location)` → nearest office

- [ ] **3.4** Load CSC center locations (for Tele-Law)
  - New file: `data/csc_centers.json` (simplified subset)
  - Content: 1000+ major CSCs + availability
  - Integration: Tele-Law booking system
  - Note: Full dataset has 400K+ centers, use major ones

- [ ] **3.5** Create Nyaya API routes
  - New file: `backend/routers/nyaya.py`
  - Routes:
    - `POST /api/nyaya/query/voice` (end-to-end)
    - `GET /api/statute/{ipc_code}` (IPC↔BNS lookup)
    - `POST /api/escalate/fir` (FIR pre-fill)
    - `GET /api/help/status` (system health)

- [ ] **3.6** Integrate Nyaya router into FastAPI app
  - File: `backend/main.py` (modify)
  - Action: `app.include_router(nyaya.router)`
  - Test: All 4 endpoints working

---

### LOW - Week 4+ (Agentic Features)

- [ ] **4.1** Create FormFiller with Playwright
  - File: `backend/agent/form_filler.py` (enhance)
  - Capability: Auto-fill gov forms (FIR, CPGRAMS, etc.)
  - CAPTCHA handling: Audio CAPTCHA + Whisper ASR
  - Test: Sandbox eCourts form

- [ ] **4.2** Create CaseTracker for persistence
  - File: `backend/tracker/case_tracker.py` (enhance)
  - Storage: SQLite (simple) or PostgreSQL (scalable)
  - Data: Case ID, user URL, status, last updated

- [ ] **4.3** Create offline legal briefing
  - Implementation: Indexeddb (client-side) for top 100 sections
  - Fallback: eSpeak-ng TTS for offline audio
  - Test: Works without internet

---

## 📊 Metrics & Verification

### For Each Todo Item

| Item | Verification Method | Success Criteria |
|------|-------------------|------------------|
| 1.1 (Sarvam ASR) | `pytest tests/test_voice_integration.py` | All voice tests pass |
| 1.2 (Corpus) | Count sections in `data/ipc_sections.json` | >500 sections indexed |
| 1.3 (RAG accuracy) | `pytest tests/test_rag.py -v` | 17+/20 queries correct (>85%) |
| 2.1 (Entity extraction) | `pytest tests/test_nyaya_extractor.py` | Precision >90% |
| 2.2 (IPC↔BNS mapping) | Count entries in JSON | 511 sections mapped |
| 2.3 (Statute resolver) | `pytest tests/test_statute_resolver.py` | All 511 mappings work |
| 2.4 (Confidence filter) | `pytest tests/test_confidence_filter.py` | Filters working correctly |
| 2.5 (RAG + entities) | Re-run `test_rag.py` | Accuracy improved to >85% |
| 3.1 (Escalation router) | `pytest tests/test_escalation_router.py` | All 5 routes working |
| 3.2-3.4 (Gov data) | File size + record count | NALSA >30 offices, CSC >500 centers |
| 3.5 (Nyaya API) | `curl -X POST localhost:8000/api/nyaya/...` | All endpoints return 200 |

---

## 🔗 File Dependencies

```
Legend: A → B means "A depends on B"

IPC↔BNS Mapping (data/ipc_bns_mapping.json)
  ↓
  ├→ StatuteResolver (backend/legal/statute_resolver.py)
  └→ NyayaEntityExtractor (backend/legal/nyaya_extractor.py)
       ↓
       → ConfidenceFilter (backend/legal/confidence_filter.py)
            ↓
            → RAG Pipeline (backend/legal/rag.py)
                 ↓
                 → EscalationRouter (backend/agent/escalation_router.py)
                      ↓
                      ├→ NALSA Offices (data/nalsa_offices.json)
                      ├→ CSC Centers (data/csc_centers.json)
                      ├→ Escalation Rules (data/escalation_rules.json)
                      └→ Nyaya Routes (backend/routers/nyaya.py)
                           ↓
                           → FastAPI App (backend/main.py)
```

**Implementation order** (respects dependencies):
1. IPC↔BNS mapping ← Start here (no dependencies)
2. StatuteResolver, NyayaEntityExtractor (use mapping)
3. ConfidenceFilter (uses entity extractor)
4. RAG enhancement (uses confidence filter)
5. Gov data files (nalsa_offices.json, etc.)
6. EscalationRouter (uses gov data + RAG)
7. Nyaya routes (uses all above)
8. FastAPI integration (glues everything)

---

## 🧪 Test Strategy

### Unit Tests (Per Component)

```bash
# Entity extraction
pytest tests/test_nyaya_extractor.py -v

# Statute resolution
pytest tests/test_statute_resolver.py -v

# Confidence filtering
pytest tests/test_confidence_filter.py -v

# Escalation routing
pytest tests/test_escalation_router.py -v
```

### Integration Tests (End-to-End)

```bash
# Complete voice query pipeline
pytest tests/test_nyaya_integration.py -v -k "voice_query"

# RAG + entity extraction
pytest tests/test_rag.py::test_entity_boosted_retrieval -v

# Escalation suggestion
pytest tests/test_nyaya_integration.py -k "escalation"
```

### Manual Testing (QA)

```bash
# Start API server
python backend/main.py

# Test Nyaya endpoint
curl -X POST http://localhost:8000/api/nyaya/query/voice \
  -F "audio=@sample_hindi.wav" \
  -F "language=hi"

# Test statute lookup
curl http://localhost:8000/api/statute/IPC-302

# Test FIR escalation
curl -X POST http://localhost:8000/api/escalate/fir \
  -H "Content-Type: application/json" \
  -d '{"incident_description": "Mere sath marof hua", ...}'
```

---

## 📈 Weekly Progress Tracking

### Week 1 (This Week)
- [ ] Sarvam API + real voice test ✓ or ✗?
- [ ] Legal corpus expanded (350 → 500+)
- [ ] RAG accuracy validated (>85%)
- **Blocker if not done**: Can't test full pipeline

### Week 2
- [ ] NyayaEntityExtractor working (90%+ precision)
- [ ] All 511 IPC↔BNS mappings verified
- [ ] Confidence filtering boosting RAG to 85%
- **Success metric**: test_rag.py passes at >85%

### Week 3
- [ ] EscalationRouter routing to 5 gov portals
- [ ] NALSA offices + CSC centers loaded
- [ ] Nyaya API endpoints all working
- **Success metric**: curl test returns 200 + data

### Week 4
- [ ] Form automation (Playwright) ready
- [ ] Case tracking system (SQLite)
- [ ] Offline legal briefing (PWA cached)
- **Success metric**: Full E2E flow works

---

## 🎯 Definition of Done (Each Todo)

For each item to be marked COMPLETE:

1. ✅ File(s) created or modified
2. ✅ Tests written and passing
3. ✅ Code follows project style guide (immutability, small functions)
4. ✅ Docstrings added (function purpose + usage)
5. ✅ No console errors or warnings
6. ✅ Committed to git with message: `feat: [description]`
7. ✅ Verified with manual test

**Example for item 2.1**:
```bash
# Step 1: File created
ls -la backend/legal/nyaya_extractor.py

# Step 2: Tests pass
pytest tests/test_nyaya_extractor.py -v
# Output:
# test_extract_offense_entities PASSED
# test_extract_statute_entities PASSED
# test_confidence_scoring PASSED
# ======================== 3 passed ========================

# Step 3: Code review
git diff backend/legal/nyaya_extractor.py | head -50

# Step 4: Commit
git add backend/legal/nyaya_extractor.py tests/test_nyaya_extractor.py
git commit -m "feat: Add legal entity extraction (NER for IPC/BNS)"

# Step 5: Verify
python -c "from backend.legal.nyaya_extractor import NyayaEntityExtractor; ex = NyayaEntityExtractor(); print('✅ Imports work')"
```

---

## 📝 Notes & Decisions

### Why This Order?

1. **Data first** (IPC↔BNS mapping): No code depends on this; foundational
2. **Extraction second** (Entity extractor): Core logic for identifying legal concepts
3. **Filtering third** (Confidence filter): Uses extractors; improves RAG
4. **Routing last** (Escalation): Uses all above; highest-level feature

### Why Split Nyaya into 3 Phases?

- **Phase 1 (CRITICAL)**: Get ASR/TTS working for voice I/O
- **Phase 2 (HIGH)**: Add legal intelligence (entity extraction, confidence filtering)
- **Phase 3 (MEDIUM)**: Add agentic features (form-filling, case tracking)

### What's NOT Included Yet?

- Police harassment detection (intent classification)
- Defence strategy generation (LLM-based, high hallucination risk)
- Offline-only mode (requires PWA + edge computing)
- WhatsApp/SMS integration (requires carrier setup)

These go in Phase 3+.

---

## 🚀 Ready to Start?

1. **Pick first todo**: Start with 1.1 (Sarvam ASR credentials)
2. **Create branch**: `git checkout -b feature/nyaya-phase2`
3. **Work through checklist**: One item at a time
4. **Verify after each**: Run tests, commit code
5. **Move to next**: Once all tests pass for item N, move to N+1

**Estimated velocity**: 2-3 items per day = 1 week to Phase 1 completion, 3 weeks to Phase 2.

**Questions to answer before starting**:
- [ ] Do you have valid Sarvam API credentials?
- [ ] Is the IPC/BNS corpus ready to be built?
- [ ] Do you want to start with entity extraction or escalation router?
- [ ] What's your deployment target (Railway, Render, or local)?

---

**Document Version**: 1.0  
**Last Updated**: March 24, 2026  
**Status**: Ready for sprint planning  
**Next Step**: Start with todo 1.1 (Sarvam testing)
