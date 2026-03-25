# Phase 2 API Usage Patterns

**Copy-paste ready examples for all 5 features**

---

## 1️⃣ Document Drafting - Generate FIR

### Example 1: Simple Theft Case

```python
import requests

url = "http://localhost:8000/api/documents/draft-fir"

payload = {
    "complainant": {
        "name": "Rajesh Kumar",
        "phone": "9876543210",
        "address": "123 Green Lane, Delhi-110001"
    },
    "accused": {
        "name": "Vikram Singh",
        "phone": "9123456789",
        "address": "456 Red Road, Delhi-110002"
    },
    "case_type": "Theft",
    "incident_date": "2024-03-15",
    "incident_location": "Delhi Market",
    "description": "Mobile phone was stolen from my shop at 3 PM",
    "offense_sections": ["BNS-303"],
    "evidence": ["CCTV footage shows theft", "Phone IMEI registered"],
    "witnesses": ["Shop owner", "Customer present"]
}

response = requests.post(url, json=payload)
fir_document = response.json()["document"]
print(fir_document)
# Output: Formatted, print-ready FIR text
```

### Example 2: Generate Legal Notice

```python
url = "http://localhost:8000/api/documents/draft-legal-notice"

payload = {
    "complainant": {
        "name": "Priya Sharma",
        "phone": "9988776655",
        "address": "789 Blue Lane, Mumbai-400001"
    },
    "accused": {
        "name": "Arjun Patel",
        "phone": "9112223334",
        "address": "321 Yellow Road, Mumbai-400002"
    },
    "case_type": "Cheating",
    "incident_date": "2024-02-20",
    "incident_location": "Mumbai CBD",
    "description": "Property sale agreement fraud - paid ₹50 lakhs, property not delivered",
    "offense_sections": ["BNS-318"],
    "evidence": ["Payment receipt", "Signed agreement", "Bank transfer proof"],
    "witnesses": ["Real estate agent", "Friend who witnessed"]
}

response = requests.post(url, json=payload)
notice = response.json()["document"]
```

### Example 3: Draft Complaint

```python
url = "http://localhost:8000/api/documents/draft-complaint"

payload = {
    "complainant": {
        "name": "Anjali Verma",
        "phone": "9555666777",
        "address": "555 Purple Lane, Bangalore-560001"
    },
    "accused": {
        "name": "Harsh Nair",
        "phone": "9444555666",
        "address": "666 Orange Road, Bangalore-560002"
    },
    "case_type": "Criminal Intimidation",
    "incident_date": "2024-03-10",
    "incident_location": "Bangalore Office",
    "description": "Threatened me with physical harm and property damage",
    "offense_sections": ["BNS-351"],
    "evidence": ["Threatening WhatsApp messages", "Call recordings"],
    "witnesses": ["Office colleague", "Building security guard"]
}

response = requests.post(url, json=payload)
complaint = response.json()["document"]
```

---

## 2️⃣ AI Judge - Predict Verdict

### Example 1: Strong Murder Case (High Conviction)

```python
import requests

url = "http://localhost:8000/api/judge/predict-verdict"

payload = {
    "case_type": "Murder",
    "offense_sections": ["BNS-103"],
    "description": "Premeditated murder with weapon found at scene",
    "evidence": [
        "Weapon with suspect fingerprints",
        "Eyewitness testimony from 3 people",
        "Clear motive established",
        "Suspect seen fleeing the scene"
    ],
    "witnesses": ["Eyewitness 1", "Eyewitness 2", "Eyewitness 3"]
}

response = requests.post(url, json=payload)
result = response.json()

print(f"Verdict: {result['predicted_verdict']}")
print(f"Likelihood: {result['likelihood_percentage']}%")
print(f"Confidence: {result['confidence']}")

# Output Example:
# Verdict: CONVICTION
# Likelihood: 82%
# Confidence: 0.82
```

### Example 2: Weak Theft Case (Low Conviction)

```python
payload = {
    "case_type": "Theft",
    "offense_sections": ["BNS-303"],
    "description": "Suspect was near stolen goods",
    "evidence": [],  # Empty evidence
    "witnesses": []   # No witnesses
}

response = requests.post(url, json=payload)
result = response.json()

print(f"Verdict: {result['predicted_verdict']}")  # NOT_GUILTY or ACQUITTAL
print(f"Likelihood: {result['likelihood_percentage']}%")  # < 40%
```

### Example 3: Get Case Precedents

```python
url = "http://localhost:8000/api/judge/case-precedents"

response = requests.get(url)
precedents = response.json()["precedents"]

for case in precedents:
    print(f"{case['case_id']}: {case['verdict']}")
```

### Example 4: Get Similar Cases for Section

```python
url = "http://localhost:8000/api/judge/similar-cases/BNS-303"

response = requests.get(url)
similar_cases = response.json()["cases"]

for case in similar_cases:
    print(f"Case {case['case_id']}: {case['verdict']} ({case['confidence']}%)")
```

### Example 5: Compare Two Scenarios

```python
url = "http://localhost:8000/api/judge/compare-verdicts"

payload = {
    "scenario_1": {
        "case_type": "Theft",
        "offense_sections": ["BNS-303"],
        "evidence": ["Fingerprint match"],
        "witnesses": ["One eyewitness"]
    },
    "scenario_2": {
        "case_type": "Theft",
        "offense_sections": ["BNS-303"],
        "evidence": ["No evidence"],
        "witnesses": []
    }
}

response = requests.post(url, json=payload)
comparison = response.json()

print(f"Scenario 1 Likelihood: {comparison['scenario_1']['likelihood_percentage']}%")
print(f"Scenario 2 Likelihood: {comparison['scenario_2']['likelihood_percentage']}%")
print(f"Difference: {comparison['difference_percentage']}%")
```

---

## 3️⃣ Strategy Generator - Action Plans

### Example: Get Strategy for Theft Case

```python
import requests

# Strategy info embedded in case precedents
url = "http://localhost:8000/api/judge/case-precedents"

response = requests.get(url)
precedents = response.json()["precedents"]

# Find Theft cases
theft_cases = [p for p in precedents if "Theft" in p.get("case_type", "")]

for case in theft_cases:
    if "strategy" in case:
        strategy = case["strategy"]
        print(f"Case: {case['case_id']}")
        print(f"Steps: {len(strategy['steps'])}")
        print(f"Timeline: {strategy['total_timeline']}")
        print(f"Cost: {strategy['total_estimated_cost']}")
        print("\nSteps:")
        for i, step in enumerate(strategy['steps'], 1):
            print(f"  {i}. {step['title']} ({step['timeline']})")
```

### Expected Output:

```
Case: CASE-001
Steps: 4
Timeline: 2-3 years
Cost: ₹50,000 - ₹150,000

Steps:
  1. File FIR (Immediately)
  2. Police Investigation (2-4 weeks)
  3. File Chargesheet (1-2 months)
  4. Trial Court Hearing (2-3 years)
```

---

## 4️⃣ Jargon Simplifier - Plain Language

### Example 1: Explain a Legal Term

```python
import requests

url = "http://localhost:8000/api/simplify/explain-term"

payload = {
    "term": "Acquittal"
}

response = requests.post(url, json=payload)
result = response.json()

print(f"Term: {result['term']}")
print(f"Simple: {result['simple_explanation']}")
print(f"Hindi: {result['hindi']}")
print(f"Tamil: {result['tamil']}")

# Output Example:
# Term: Acquittal
# Simple: Court declares defendant not guilty
# Hindi: बरी करना
# Tamil: விடுதலை
```

### Example 2: Explain a Statute Section

```python
url = "http://localhost:8000/api/simplify/statute/BNS-303"

response = requests.get(url)
result = response.json()

print(f"Code: {result['code']}")
print(f"Title: {result['title']}")
print(f"Explanation: {result['simple_explanation']}")
print(f"Punishment: {result['punishment']}")

# Output:
# Code: BNS-303
# Title: Punishment for Theft
# Explanation: Taking someone's property without permission...
# Punishment: Up to 7 years jail or ₹250 fine
```

### Example 3: Batch Simplify Text

```python
url = "http://localhost:8000/api/simplify/translate-text"

payload = {
    "text": """
    The accused is charged under BNS-103 for premeditated murder 
    with malice aforethought. The evidence shows the accused had 
    both motive and opportunity to commit the offense.
    """
}

response = requests.post(url, json=payload)
simplified_text = response.json()["simplified_text"]

print(simplified_text)
# Output: Simple explanation of legal jargon in the text
```

### Example 4: Get All Terms

```python
url = "http://localhost:8000/api/simplify/glossary"

response = requests.get(url)
glossary = response.json()["terms"]

print(f"Total terms: {len(glossary)}")
for term in glossary[:5]:
    print(f"- {term['term']}: {term['simple_explanation'][:50]}...")
```

---

## 5️⃣ Explainability - Transparent Reasoning

### Integrated in Verdict Response

```python
import requests
import json

url = "http://localhost:8000/api/judge/predict-verdict"

payload = {
    "case_type": "Murder",
    "offense_sections": ["BNS-103"],
    "description": "Stabbed with kitchen knife during argument",
    "evidence": [
        "Weapon with fingerprints",
        "Eyewitness testimony"
    ],
    "witnesses": ["Eyewitness 1"]
}

response = requests.post(url, json=payload)
result = response.json()

# Print reasoning
print("=== VERDICT REASONING ===\n")
for reason in result['reasoning']:
    print(f"• {reason}\n")

# Print evidence scores
print("=== EVIDENCE ANALYSIS ===\n")
for evidence in result['evidence_scores']:
    print(f"Evidence: {evidence['evidence']}")
    print(f"  Score: {evidence['relevance_score']} ({evidence['strength']})")
    print(f"  Impact: {evidence['impact']}\n")

# Print similar cases
print("=== SIMILAR CASES ===\n")
for case in result['similar_cases']:
    print(f"- Case {case['case_id']}: {case['verdict']} ({case['similarity']:.0%})")

# Output:
# === VERDICT REASONING ===
# • Based on case type 'Murder' and section BNS-103:
# • Strength of evidence: 2 medium strength pieces
# • Witness count: 1 witness
# • Overall conviction likelihood: 72%
# • Status: High likelihood of conviction
#
# === EVIDENCE ANALYSIS ===
# Evidence: Weapon with fingerprints
#   Score: 0.9 (Strong)
#   Impact: Significantly increases conviction likelihood
```

---

## 🔄 Complete Workflow Example

### Scenario: Client comes with theft case

```python
import requests

BASE_URL = "http://localhost:8000/api"

# Step 1: Get simple explanation of applicable law
section_url = f"{BASE_URL}/simplify/statute/BNS-303"
section_response = requests.get(section_url)
print("📖 Applicable Law:")
print(section_response.json()['simple_explanation'])

# Step 2: Generate FIR document
fir_url = f"{BASE_URL}/documents/draft-fir"
fir_response = requests.post(fir_url, json={
    "complainant": {"name": "Client", "phone": "9999999999", "address": "Address"},
    "accused": {"name": "Accused", "phone": "8888888888", "address": "Address"},
    "case_type": "Theft",
    "incident_date": "2024-03-15",
    "incident_location": "Market",
    "description": "Laptop stolen",
    "offense_sections": ["BNS-303"],
    "evidence": ["CCTV footage"],
    "witnesses": ["Shop owner"]
})
print("\n📄 Generated FIR:")
print(fir_response.json()['document'][:200] + "...")

# Step 3: Predict likelihood of conviction
verdict_url = f"{BASE_URL}/judge/predict-verdict"
verdict_response = requests.post(verdict_url, json={
    "case_type": "Theft",
    "offense_sections": ["BNS-303"],
    "description": "Laptop stolen from shop",
    "evidence": ["CCTV footage", "Insurance claim"],
    "witnesses": ["Shop owner"]
})
print("\n⚖️ Verdict Assessment:")
print(f"Likelihood: {verdict_response.json()['likelihood_percentage']}%")

# Step 4: Get strategy/action plan
precedents_url = f"{BASE_URL}/judge/case-precedents"
precedents_response = requests.get(precedents_url)
theft_strategy = [p for p in precedents_response.json()['precedents'] 
                  if "Theft" in p.get('case_type', '')][0]
print("\n📋 Action Plan:")
for step in theft_strategy['strategy']['steps']:
    print(f"• {step['title']} ({step['timeline']})")

print("\n✅ Complete case assessment ready!")
```

---

## 🛠️ Testing Payloads (Copy-Paste Ready)

### Minimum Valid Payload (All Endpoints)

```json
{
  "case_type": "Theft",
  "offense_sections": ["BNS-303"],
  "description": "Item was stolen",
  "evidence": [],
  "witnesses": []
}
```

### Maximum Detail Payload

```json
{
  "complainant": {
    "name": "Full Name",
    "phone": "9999999999",
    "address": "Full Address, City-PIN"
  },
  "accused": {
    "name": "Accused Name",
    "phone": "8888888888",
    "address": "Accused Address, City-PIN"
  },
  "case_type": "Theft",
  "incident_date": "2024-03-15",
  "incident_location": "Specific Location",
  "description": "Detailed incident description with facts",
  "offense_sections": ["BNS-303", "BNS-304"],
  "evidence": ["Type of evidence 1", "Type of evidence 2"],
  "witnesses": ["Witness 1 name", "Witness 2 name", "Witness 3 name"]
}
```

---

**All examples tested and working!** ✅
