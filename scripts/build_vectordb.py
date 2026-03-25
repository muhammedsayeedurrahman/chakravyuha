"""Build ChromaDB vector store from BNS/IPC JSON data."""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import CHROMA_PERSIST_DIR, DATA_DIR, EMBEDDING_MODEL


def load_sections(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["sections"]


def build_documents(sections: list[dict], law: str) -> tuple[list[str], list[dict], list[str]]:
    """Convert sections to ChromaDB documents.

    Returns:
        Tuple of (documents, metadatas, ids).
    """
    documents = []
    metadatas = []
    ids = []

    for section in sections:
        # Create a rich document combining all searchable text
        doc_parts = [
            f"Section {section['section_id']}: {section['title']}",
            section.get("description", ""),
            f"Punishment: {section.get('punishment', '')}",
        ]
        keywords = section.get("keywords", [])
        if keywords:
            doc_parts.append(f"Keywords: {', '.join(keywords)}")

        document = "\n".join(doc_parts)
        documents.append(document)

        metadatas.append({
            "section_id": section["section_id"],
            "title": section["title"],
            "law": law,
            "punishment": section.get("punishment", ""),
            "cognizable": str(section.get("cognizable", "")),
            "bailable": str(section.get("bailable", "")),
            "chapter": section.get("chapter", ""),
        })

        ids.append(f"{law}_{section['section_id']}")

    return documents, metadatas, ids


def main():
    print("Building ChromaDB vector store...")
    print(f"  Data dir: {DATA_DIR}")
    print(f"  Persist dir: {CHROMA_PERSIST_DIR}")
    print(f"  Embedding model: {EMBEDDING_MODEL}")

    import chromadb
    from chromadb.utils import embedding_functions

    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )

    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

    # Delete existing collection if present
    try:
        client.delete_collection("legal_sections")
        print("  Deleted existing collection.")
    except Exception:
        pass

    collection = client.create_collection(
        name="legal_sections",
        embedding_function=ef,
        metadata={"description": "Indian legal sections (BNS + IPC)"},
    )

    # Load BNS sections
    bns_path = DATA_DIR / "bns_sections.json"
    if bns_path.exists():
        bns_sections = load_sections(bns_path)
        docs, metas, doc_ids = build_documents(bns_sections, "BNS")
        collection.add(documents=docs, metadatas=metas, ids=doc_ids)
        print(f"  Added {len(docs)} BNS sections")

    # Load IPC sections
    ipc_path = DATA_DIR / "ipc_sections.json"
    if ipc_path.exists():
        ipc_sections = load_sections(ipc_path)
        docs, metas, doc_ids = build_documents(ipc_sections, "IPC")
        collection.add(documents=docs, metadatas=metas, ids=doc_ids)
        print(f"  Added {len(docs)} IPC sections")

    total = collection.count()
    print(f"\nVector DB built successfully with {total} documents.")
    print(f"Stored at: {CHROMA_PERSIST_DIR}")


if __name__ == "__main__":
    main()
