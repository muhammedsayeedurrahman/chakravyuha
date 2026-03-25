"""Build an augmented ChromaDB index with synthetic Q&A pairs.

This extends the base vector index with question embeddings, so that
user queries match more naturally (query-to-query similarity > query-to-document).

Usage:
    python scripts/build_augmented_index.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import CHROMA_PERSIST_DIR, DATA_DIR, EMBEDDING_MODEL


def main():
    print("Building augmented ChromaDB index...")
    print(f"  Persist dir: {CHROMA_PERSIST_DIR}")
    print(f"  Embedding model: {EMBEDDING_MODEL}")

    # Step 1: Generate training data if not present
    qa_path = DATA_DIR / "training_qa.json"
    if not qa_path.exists():
        print("  Generating training Q&A pairs first...")
        from scripts.generate_training_data import main as gen_main
        gen_main()

    with open(qa_path, "r", encoding="utf-8") as f:
        qa_data = json.load(f)

    qa_pairs = qa_data.get("qa_pairs", [])
    print(f"  Loaded {len(qa_pairs)} Q&A pairs")

    # Step 2: Run the base vectordb build
    print("\n--- Building base index ---")
    from scripts.build_vectordb import main as build_base
    build_base()

    # Step 3: Add Q&A augmentation documents
    print("\n--- Adding Q&A augmentation ---")
    import chromadb
    from chromadb.utils import embedding_functions

    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )

    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    collection = client.get_collection(
        name="legal_sections",
        embedding_function=ef,
    )

    # Deduplicate Q&A by section_id (keep diverse questions per section)
    seen_per_section: dict[str, int] = {}
    max_per_section = 5  # Limit augmentation docs per section to avoid index bloat

    documents = []
    metadatas = []
    ids = []

    for i, pair in enumerate(qa_pairs):
        section_id = pair["section_id"]
        count = seen_per_section.get(section_id, 0)
        if count >= max_per_section:
            continue
        seen_per_section[section_id] = count + 1

        # Use the question as the document (for query-to-query matching)
        doc = f"Question: {pair['question']}\nAnswer: {pair['answer'][:300]}"
        documents.append(doc)

        metadatas.append({
            "section_id": section_id,
            "title": pair.get("category", ""),
            "law": pair["law"],
            "type": "qa_augmentation",
            "punishment": "",
            "cognizable": "",
            "bailable": "",
            "chapter": "",
        })

        ids.append(f"qa_{pair['law']}_{section_id}_{count}")

    if documents:
        # Add in batches (ChromaDB has batch size limits)
        batch_size = 500
        for start in range(0, len(documents), batch_size):
            end = min(start + batch_size, len(documents))
            collection.add(
                documents=documents[start:end],
                metadatas=metadatas[start:end],
                ids=ids[start:end],
            )
            print(f"  Added batch {start}-{end}")

    total = collection.count()
    print(f"\nAugmented index built: {total} total documents")
    print(f"  Base sections + {len(documents)} Q&A augmentation docs")
    print(f"  Stored at: {CHROMA_PERSIST_DIR}")


if __name__ == "__main__":
    main()
