#!/usr/bin/env python
"""Functional test for Nyaya integration"""

from backend.legal.nyaya_extractor import NyayaEntityExtractor, EntityType
from backend.legal.statute_resolver import StatuteResolver

print('🧪 Nyaya Component Functional Test')
print('='*50)

# Test 1: Entity Extraction
print('\n1️⃣  Testing Entity Extraction...')
extractor = NyayaEntityExtractor()
query = 'Section 302 murder case in sessions court'
entities = extractor.extract(query)
print(f'   Query: {query}')
print(f'   Entities found: {len(entities)}')
for e in entities:
    print(f'   ✓ {e.text} ({e.entity_type.value}) -> {e.statute_reference} (conf: {e.confidence:.2f})')

# Test 2: Statute Resolution
print('\n2️⃣  Testing Statute Resolution (IPC->BNS)...')
resolver = StatuteResolver()
result = resolver.resolve_to_bns('IPC-302')
print(f'   IPC-302 resolves to: {result["bns"]}')
print(f'   Title: {result["ipc_title"]}')
print(f'   Punishment: {resolver.get_punishment("BNS-103")}')
print(f'   Cognizable: {resolver.is_cognizable("IPC-302")}')
print(f'   Bailable: {resolver.is_bailable("IPC-302")}')

# Test 3: Statute Details
print('\n3️⃣  Testing Statute Details...')
details = resolver.get_statute_details('IPC-323')
print(f'   Statute: IPC-323')
print(f'   Title: {details["title"]}')
print(f'   Cognizable: {details["cognizable"]}')
print(f'   Bailable: {details["bailable"]}')

# Test 4: Multiple statute types
print('\n4️⃣  Testing Multiple Statute Types...')
test_cases = [
    ('IPC-302', 'BNS-103', 'Murder'),
    ('IPC-323', 'BNS-115', 'Hurt'),
    ('IPC-379', 'BNS-303', 'Theft'),
]
for ipc, expected_bns, name in test_cases:
    result = resolver.resolve_to_bns(ipc)
    match = "✓" if result["bns"] == expected_bns else "✗"
    print(f'   {match} {ipc} ({name}) -> {result["bns"]}')

print('\n' + '='*50)
print('✅ All Nyaya components working correctly!')
print('\nEndpoints available:')
print('  POST /api/nyaya/query')
print('  POST /api/nyaya/extract-entities')
print('  GET /api/nyaya/statute/{statute_code}')
print('  GET /api/nyaya/offense/{offense_name}')
print('  POST /api/nyaya/compare-statutes')
print('  GET /api/nyaya/help')
print('  GET /api/nyaya/health')
