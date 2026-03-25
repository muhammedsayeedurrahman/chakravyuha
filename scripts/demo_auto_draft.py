#!/usr/bin/env python
"""
Automated Demo: Agentic Complaint Drafting Pipeline
====================================================

Runs a complete end-to-end instance of the complaint drafting agent:
  Narrative → Entity Extraction → Statute Resolution → Document Classification
  → LLM-Powered Draft → Legal Strategy → Final Output

Usage:
    python scripts/demo_auto_draft.py
    python scripts/demo_auto_draft.py --narrative "Someone stole my bike"
    python scripts/demo_auto_draft.py --type LEGAL_NOTICE
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Fix Windows console encoding
import io
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


# ── Pretty-print helpers ────────────────────────────────────────────────────

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def banner(text: str) -> None:
    width = 72
    print(f"\n{CYAN}{'=' * width}")
    print(f"  {BOLD}{text}{RESET}{CYAN}")
    print(f"{'=' * width}{RESET}")


def step(num: int, title: str) -> None:
    print(f"\n{GREEN}{BOLD}[Step {num}]{RESET} {GREEN}{title}{RESET}")
    print(f"{DIM}{'─' * 60}{RESET}")


def info(key: str, value: str) -> None:
    print(f"  {YELLOW}{key}:{RESET} {value}")


def error(msg: str) -> None:
    print(f"\n{RED}{BOLD}ERROR:{RESET} {RED}{msg}{RESET}")


# ── Demo scenarios ──────────────────────────────────────────────────────────

DEMO_SCENARIOS = {
    "theft": {
        "narrative": (
            "My neighbor Ravi Sharma stole my mobile phone from my house "
            "on March 20, 2026. I was at home in Delhi when he entered my house "
            "without permission and took my iPhone 15 Pro worth Rs 1,50,000. "
            "I have CCTV footage of him entering and leaving with the phone. "
            "My friend Priya was also present and witnessed the incident."
        ),
        "complainant_name": "Raj Kumar",
        "complainant_phone": "9876543210",
        "complainant_address": "123 Main Street, Chandni Chowk, Delhi-110001",
        "complainant_email": "raj.kumar@example.com",
    },
    "cheating": {
        "narrative": (
            "My business partner Suresh Mehta cheated me of Rs 5,00,000. "
            "He took the money as investment for a restaurant business in Mumbai "
            "on January 15, 2026 but never started the business. He has been "
            "avoiding my calls and has blocked me on WhatsApp. I have bank "
            "transfer receipts and WhatsApp chat screenshots as evidence."
        ),
        "complainant_name": "Priya Sharma",
        "complainant_phone": "9123456789",
        "complainant_address": "456 Park Avenue, Andheri West, Mumbai-400058",
        "complainant_email": "priya.s@example.com",
    },
    "hurt": {
        "narrative": (
            "Yesterday at the local market near Connaught Place, Delhi, "
            "an unknown person attacked me and hit me with a wooden stick. "
            "I suffered injuries on my head and left arm. There were several "
            "witnesses at the market. I went to AIIMS hospital for treatment "
            "and have the medical report."
        ),
        "complainant_name": "Amit Verma",
        "complainant_phone": "9988776655",
        "complainant_address": "789 Ring Road, New Delhi-110001",
        "complainant_email": "",
    },
}


# ── Main demo ───────────────────────────────────────────────────────────────

def run_demo(
    narrative: str,
    complainant_name: str = "Demo User",
    complainant_phone: str = "9999999999",
    complainant_address: str = "",
    complainant_email: str = "",
    preferred_type: str = "",
    language: str = "en-IN",
) -> None:
    """Run the full agentic complaint drafting pipeline with step-by-step output."""

    banner("CHAKRAVYUHA — Agentic Complaint Drafting Demo")

    print(f"\n{DIM}Initializing pipeline components...{RESET}")
    t0 = time.time()

    from backend.agent.complaint_drafter_agent import ComplaintDrafterAgent
    agent = ComplaintDrafterAgent()

    init_time = time.time() - t0
    print(f"{DIM}Initialized in {init_time:.2f}s{RESET}")

    # ── Step 1: Show input ──────────────────────────────────────────────
    step(1, "INPUT — User Narrative")
    print(f"\n  \"{narrative[:200]}{'...' if len(narrative) > 200 else ''}\"")
    info("Complainant", complainant_name)
    info("Phone", complainant_phone)
    if preferred_type:
        info("Preferred doc type", preferred_type)

    # ── Step 2: Entity extraction ───────────────────────────────────────
    step(2, "ENTITY EXTRACTION — Analyzing narrative")
    t1 = time.time()

    extracted = agent._analyze_narrative(narrative, language)

    extract_time = time.time() - t1
    if extracted is None:
        error("No legal entities found. Narrative may not describe a legal incident.")
        return

    info("Offense detected", f"{extracted.offense.title()} (confidence: {extracted.offense_confidence:.0%})")
    info("BNS Sections", ", ".join(extracted.bns_sections) or "None")
    info("IPC Equivalents", ", ".join(extracted.ipc_sections) or "None")
    info("Jurisdiction", extracted.jurisdiction)
    info("Cognizable", "Yes" if extracted.cognizable else "No")
    info("Bailable", "Yes" if extracted.bailable else "No")
    info("Punishment", extracted.punishment_summary)
    info("Extraction time", f"{extract_time:.2f}s")

    # ── Step 3: Document classification ─────────────────────────────────
    step(3, "DOCUMENT CLASSIFICATION — Selecting document type")
    doc_type = agent._classify_document_type(extracted, narrative, preferred_type)
    doc_labels = {"FIR": "First Information Report", "LEGAL_NOTICE": "Legal Notice", "COMPLAINT": "Complaint Petition"}
    info("Selected type", f"{doc_type} ({doc_labels.get(doc_type, doc_type)})")

    reason = ""
    if doc_type == "FIR":
        reason = "Criminal offense + cognizable = police FIR"
    elif doc_type == "LEGAL_NOTICE":
        reason = "Demand/warning keywords detected"
    elif doc_type == "COMPLAINT":
        reason = "Civil/consumer dispute"
    info("Reason", reason)

    # ── Step 4: Context extraction ──────────────────────────────────────
    step(4, "CONTEXT EXTRACTION — Dates, locations, names from narrative")
    incident_date = agent._extract_date(narrative)
    incident_location = agent._extract_location(narrative)
    accused_name = agent._extract_accused_name(narrative)
    info("Incident date", incident_date or "(not found)")
    info("Incident location", incident_location or "(not found)")
    info("Accused name", accused_name or "(not found)")

    # ── Step 5: Missing fields ──────────────────────────────────────────
    step(5, "MISSING FIELDS — Checking completeness")
    missing = agent._identify_missing_fields(
        complainant_name=complainant_name,
        complainant_phone=complainant_phone,
        accused_name=accused_name or "Unknown",
        incident_date=incident_date,
        incident_location=incident_location,
    )
    if missing:
        for field in missing:
            print(f"  {RED}[MISSING]{RESET} {field.replace('_', ' ').title()}")
    else:
        print(f"  {GREEN}All critical fields present!{RESET}")

    # ── Step 6: Full pipeline ───────────────────────────────────────────
    step(6, "DOCUMENT GENERATION — Running full agentic pipeline")
    print(f"\n{DIM}  Calling LLM for document generation (this may take 10-30s)...{RESET}")
    t2 = time.time()

    result = agent.auto_draft(
        narrative=narrative,
        complainant_name=complainant_name,
        complainant_phone=complainant_phone,
        complainant_address=complainant_address,
        complainant_email=complainant_email,
        preferred_doc_type=preferred_type,
        language=language,
    )

    gen_time = time.time() - t2

    info("Status", result.status)
    info("Document type", result.document_type)
    info("Generation time", f"{gen_time:.2f}s")
    info("Content length", f"{len(result.content)} chars")

    # ── Step 7: Strategy ────────────────────────────────────────────────
    step(7, "LEGAL STRATEGY — Next steps & cost estimate")
    if result.strategy_summary:
        s = result.strategy_summary
        info("Recommended forum", s.get("recommended_forum", ""))
        info("Timeline", s.get("total_timeline", ""))
        info("Estimated cost", s.get("total_estimated_cost", ""))
        info("Next action", s.get("next_immediate_action", ""))
        info("Mediation recommended", "Yes" if s.get("mediation_recommended") else "No")

        if s.get("evidence_checklist"):
            print(f"\n  {YELLOW}Evidence checklist:{RESET}")
            for item in s["evidence_checklist"]:
                print(f"    [ ] {item}")

        if s.get("steps"):
            print(f"\n  {YELLOW}Action steps:{RESET}")
            for step_info in s["steps"]:
                print(f"    {step_info['step']}. {step_info['title']} "
                      f"({step_info['timeline']}) — {step_info['cost']}")

    # ── Step 8: Final document ──────────────────────────────────────────
    banner("GENERATED DOCUMENT")
    print(result.content)

    # ── Summary ─────────────────────────────────────────────────────────
    total_time = time.time() - t0
    banner("PIPELINE SUMMARY")
    info("Total time", f"{total_time:.2f}s")
    info("Document type", result.document_type)
    info("Offense", extracted.offense.title())
    info("Confidence", f"{result.confidence:.0%}")
    info("Sections", ", ".join(result.applicable_sections))
    info("Missing fields", ", ".join(result.missing_fields) if result.missing_fields else "None")
    info("Status", result.status)

    if result.error:
        error(result.error)

    print()


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Demo: Agentic Complaint Drafting Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/demo_auto_draft.py\n"
            "  python scripts/demo_auto_draft.py --scenario cheating\n"
            '  python scripts/demo_auto_draft.py --narrative "My phone was stolen"\n'
            "  python scripts/demo_auto_draft.py --type LEGAL_NOTICE\n"
        ),
    )
    parser.add_argument(
        "--scenario",
        choices=list(DEMO_SCENARIOS.keys()),
        default="theft",
        help="Pre-built demo scenario (default: theft)",
    )
    parser.add_argument("--narrative", type=str, help="Custom narrative text")
    parser.add_argument("--name", type=str, help="Complainant name")
    parser.add_argument("--phone", type=str, help="Complainant phone")
    parser.add_argument("--type", type=str, default="", help="Force document type: FIR, LEGAL_NOTICE, COMPLAINT")
    parser.add_argument("--lang", type=str, default="en-IN", help="Language code (default: en-IN)")

    args = parser.parse_args()

    # Use custom narrative or pre-built scenario
    if args.narrative:
        run_demo(
            narrative=args.narrative,
            complainant_name=args.name or "Demo User",
            complainant_phone=args.phone or "9999999999",
            preferred_type=args.type,
            language=args.lang,
        )
    else:
        scenario = DEMO_SCENARIOS[args.scenario]
        run_demo(
            narrative=scenario["narrative"],
            complainant_name=args.name or scenario["complainant_name"],
            complainant_phone=args.phone or scenario["complainant_phone"],
            complainant_address=scenario.get("complainant_address", ""),
            complainant_email=scenario.get("complainant_email", ""),
            preferred_type=args.type,
            language=args.lang,
        )


if __name__ == "__main__":
    main()
