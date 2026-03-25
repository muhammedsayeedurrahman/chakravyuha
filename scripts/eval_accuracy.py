"""Evaluate legal section accuracy against test queries."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import DATA_DIR
from backend.legal.rag import LegalRAG
from backend.legal.sections import SectionLookup


def load_test_queries() -> list[dict]:
    path = DATA_DIR / "test_queries.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["queries"]


def evaluate_rag(rag: LegalRAG, queries: list[dict]) -> dict:
    """Evaluate RAG accuracy on test queries.

    Returns:
        Dict with accuracy metrics.
    """
    total = len(queries)
    correct = 0
    partial = 0
    missed = 0
    results = []

    for q in queries:
        query_text = q["query"]
        expected_bns = set(q.get("expected_bns", []))
        expected_ipc = set(q.get("expected_ipc", []))
        expected_all = expected_bns | expected_ipc

        rag_result = rag.retrieve_with_correction(query_text)
        retrieved_ids = {s["section_id"] for s in rag_result.get("sections", [])}

        # Check if any expected section was retrieved
        found_expected = retrieved_ids & expected_all

        if found_expected == expected_all:
            status = "CORRECT"
            correct += 1
        elif found_expected:
            status = "PARTIAL"
            partial += 1
        else:
            status = "MISSED"
            missed += 1

        results.append({
            "id": q["id"],
            "query": query_text,
            "expected": sorted(expected_all),
            "retrieved": sorted(retrieved_ids),
            "status": status,
            "confidence": rag_result.get("confidence", "none"),
        })

    accuracy = correct / total if total > 0 else 0
    partial_accuracy = (correct + partial) / total if total > 0 else 0

    return {
        "total": total,
        "correct": correct,
        "partial": partial,
        "missed": missed,
        "accuracy": round(accuracy * 100, 1),
        "partial_accuracy": round(partial_accuracy * 100, 1),
        "results": results,
    }


def evaluate_keyword_search(lookup: SectionLookup, queries: list[dict]) -> dict:
    """Evaluate keyword search accuracy."""
    total = len(queries)
    correct = 0
    results = []

    for q in queries:
        query_text = q["query"]
        expected_bns = set(q.get("expected_bns", []))

        # Extract key terms for search
        search_results = lookup.search_sections(query_text.split()[0])
        retrieved_ids = {s["section_id"] for s in search_results[:5]}

        found = bool(retrieved_ids & expected_bns)
        if found:
            correct += 1

        results.append({
            "id": q["id"],
            "query": query_text,
            "found": found,
        })

    accuracy = correct / total if total > 0 else 0
    return {
        "total": total,
        "correct": correct,
        "accuracy": round(accuracy * 100, 1),
        "results": results,
    }


def main():
    print("=" * 60)
    print("CHAKRAVYUHA — Legal Section Accuracy Evaluation")
    print("=" * 60)

    queries = load_test_queries()
    print(f"\nLoaded {len(queries)} test queries.\n")

    # Evaluate RAG
    rag = LegalRAG()
    if rag.is_ready:
        print("--- RAG Pipeline Evaluation ---")
        rag_metrics = evaluate_rag(rag, queries)
        print(f"  Total queries: {rag_metrics['total']}")
        print(f"  Exact match:   {rag_metrics['correct']} ({rag_metrics['accuracy']}%)")
        print(f"  Partial match: {rag_metrics['partial']}")
        print(f"  Missed:        {rag_metrics['missed']}")
        print(f"  Combined accuracy (exact + partial): {rag_metrics['partial_accuracy']}%")
        print()

        # Print details for missed
        missed = [r for r in rag_metrics["results"] if r["status"] == "MISSED"]
        if missed:
            print("  MISSED queries:")
            for m in missed:
                print(f"    Q{m['id']}: \"{m['query']}\"")
                print(f"         Expected: {m['expected']}, Got: {m['retrieved']}")
    else:
        print("RAG not ready — run `python scripts/build_vectordb.py` first.")
        print("Skipping RAG evaluation.\n")

    # Evaluate keyword search
    print("\n--- Keyword Search Evaluation ---")
    lookup = SectionLookup()
    kw_metrics = evaluate_keyword_search(lookup, queries)
    print(f"  Total queries: {kw_metrics['total']}")
    print(f"  Found: {kw_metrics['correct']} ({kw_metrics['accuracy']}%)")

    print("\n" + "=" * 60)
    print("Evaluation complete.")


if __name__ == "__main__":
    main()
