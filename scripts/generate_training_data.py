"""Generate synthetic Q&A training data and build an augmented vector index.

Usage:
    python scripts/generate_training_data.py           # generate Q&A pairs
    python scripts/generate_training_data.py --augment  # rebuild augmented index
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import CHROMA_PERSIST_DIR, DATA_DIR, EMBEDDING_MODEL

OUTPUT_PATH = DATA_DIR / "synthetic_qa.json"

# ── Template-based synthetic Q&A generator ──────────────────────────────────

QUESTION_TEMPLATES = [
    "What is {section_id}?",
    "Explain {title} under Indian law.",
    "What is the punishment for {title_lower}?",
    "Is {title_lower} bailable or non-bailable?",
    "Is {title_lower} a cognizable offence?",
    "What section of {law_name} deals with {title_lower}?",
    "If someone commits {title_lower}, what happens?",
    "My {relation} was a victim of {title_lower}. What law applies?",
    "Can you explain {section_id} - {title}?",
    "What are the legal consequences of {title_lower}?",
    "How is {title_lower} defined in {law_name}?",
    "What should I do if I am accused of {title_lower}?",
    "Is {title_lower} punishable by imprisonment?",
]

RELATIONS = ["friend", "brother", "sister", "neighbour", "colleague", "relative"]


def load_sections(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["sections"]


def generate_qa_pairs(sections: list[dict], law: str) -> list[dict]:
    """Generate synthetic question-answer pairs for each section."""
    law_name = "BNS 2023" if law == "BNS" else "IPC 1860"
    pairs: list[dict] = []

    for section in sections:
        sid = section["section_id"]
        title = section.get("title", "Unknown")
        title_lower = title.lower()
        description = section.get("description", "")
        punishment = section.get("punishment", "Not specified")
        bailable = "bailable" if section.get("bailable") else "non-bailable"
        cognizable = "cognizable" if section.get("cognizable") else "non-cognizable"

        answer_base = (
            f"{sid} ({law_name}) deals with {title}. "
            f"{description[:300]} "
            f"This offence is {cognizable} and {bailable}. "
            f"Punishment: {punishment}."
        )

        for template in QUESTION_TEMPLATES:
            question = template.format(
                section_id=sid,
                title=title,
                title_lower=title_lower,
                law_name=law_name,
                relation=random.choice(RELATIONS),
            )
            pairs.append({
                "question": question,
                "answer": answer_base,
                "section_id": sid,
                "law": law,
                "source": "synthetic",
            })

    return pairs


def generate_all() -> list[dict]:
    """Generate synthetic Q&A for all BNS and IPC sections."""
    all_pairs: list[dict] = []

    bns_path = DATA_DIR / "bns_sections.json"
    if bns_path.exists():
        bns = load_sections(bns_path)
        all_pairs.extend(generate_qa_pairs(bns, "BNS"))
        print(f"  Generated {len(bns) * len(QUESTION_TEMPLATES)} BNS Q&A pairs")

    ipc_path = DATA_DIR / "ipc_sections.json"
    if ipc_path.exists():
        ipc = load_sections(ipc_path)
        all_pairs.extend(generate_qa_pairs(ipc, "IPC"))
        print(f"  Generated {len(ipc) * len(QUESTION_TEMPLATES)} IPC Q&A pairs")

    return all_pairs


def build_augmented_index(qa_pairs: list[dict]) -> None:
    """Rebuild the ChromaDB index with augmented Q&A documents."""
    import chromadb
    from chromadb.utils import embedding_functions

    print("\nBuilding augmented vector index...")

    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

    # Rebuild original index first (from build_vectordb.py)
    try:
        client.delete_collection("legal_sections")
    except Exception:
        pass

    collection = client.create_collection(
        name="legal_sections",
        embedding_function=ef,
        metadata={"description": "Indian legal sections (BNS + IPC) + augmented Q&A"},
    )

    # Add original sections
    for law, filename in [("BNS", "bns_sections.json"), ("IPC", "ipc_sections.json")]:
        path = DATA_DIR / filename
        if not path.exists():
            continue
        sections = load_sections(path)
        from scripts.build_vectordb import build_documents

        docs, metas, ids = build_documents(sections, law)
        collection.add(documents=docs, metadatas=metas, ids=ids)
        print(f"  Added {len(docs)} original {law} sections")

    # Add Q&A pairs as augmented documents
    batch_size = 100
    for i in range(0, len(qa_pairs), batch_size):
        batch = qa_pairs[i : i + batch_size]
        documents = [f"Q: {p['question']}\nA: {p['answer']}" for p in batch]
        metadatas = [
            {
                "section_id": p["section_id"],
                "title": p["question"][:100],
                "law": p["law"],
                "punishment": "",
                "cognizable": "",
                "bailable": "",
                "chapter": "",
            }
            for p in batch
        ]
        ids = [f"qa_{p['law']}_{p['section_id']}_{j}" for j, p in enumerate(batch, i)]
        collection.add(documents=documents, metadatas=metadatas, ids=ids)

    total = collection.count()
    print(f"\nAugmented index built with {total} total documents.")
    print(f"Stored at: {CHROMA_PERSIST_DIR}")


def main() -> None:
    print("Generating synthetic training data...\n")
    qa_pairs = generate_all()

    # Save to JSON
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"pairs": qa_pairs, "count": len(qa_pairs)}, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(qa_pairs)} Q&A pairs to {OUTPUT_PATH}")

    if "--augment" in sys.argv:
        build_augmented_index(qa_pairs)


if __name__ == "__main__":
    main()
